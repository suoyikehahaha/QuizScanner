"""Extract multiple-choice questions from a teacher-formatted DOCX file."""

import base64
import binascii
import os
import re
import zipfile
from xml.etree import ElementTree


MAX_DOCX_BYTES = 8 * 1024 * 1024
MAX_ZIP_EXPANDED_BYTES = 24 * 1024 * 1024
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

_QUESTION = re.compile(
    r"^(?:第\s*)?(?P<num>\d{1,3})\s*[.．、:：)]\s*(?P<text>.*)$|"
    r"^[（(]\s*(?P<num2>\d{1,3})\s*[）)]\s*(?P<text2>.*)$"
)
_OPTION = re.compile(
    r"^(?:[（(]\s*([A-DＡ-Ｄ])\s*[）)]|([A-DＡ-Ｄ])\s*[.．、:：])\s*(.*)$",
    re.IGNORECASE,
)
_ANSWER = re.compile(r"^(?:参考)?答案\s*[:：]\s*([A-DＡ-Ｄ])\s*$", re.IGNORECASE)
_ANSWER_PAIRS = re.compile(r"(?<!\w)(\d{1,3})\s*[.．、:：)）]?\s*([A-DＡ-Ｄ])", re.IGNORECASE)
_MATERIAL_START = re.compile(r"^【(?:阅读)?材料】\s*(.*)$")


def _letter(value):
    value = value.upper().translate(str.maketrans("ＡＢＣＤ", "ABCD"))
    return value if value in "ABCD" else None


def _paragraph_text(paragraph):
    parts = []
    for node in paragraph.iter():
        if node.tag == W + "t":
            parts.append(node.text or "")
        elif node.tag == W + "tab":
            parts.append("\t")
        elif node.tag in (W + "br", W + "cr"):
            parts.append("\n")
    return "".join(parts)


def _body_paragraphs(node):
    if node.tag == W + "p":
        yield _paragraph_text(node)
        return
    for child in node:
        yield from _body_paragraphs(child)


def _read_docx(blob):
    try:
        with zipfile.ZipFile(__import__("io").BytesIO(blob)) as archive:
            infos = archive.infolist()
            if sum(info.file_size for info in infos) > MAX_ZIP_EXPANDED_BYTES:
                raise ValueError("Word 文档展开后超过 24 MB。")
            try:
                xml = archive.read("word/document.xml")
            except KeyError as exc:
                raise ValueError("文件中没有找到 Word 正文。") from exc
    except zipfile.BadZipFile as exc:
        raise ValueError("文件不是有效的 DOCX 文档。") from exc
    if len(xml) > MAX_ZIP_EXPANDED_BYTES:
        raise ValueError("Word 正文过大，无法安全解析。")
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise ValueError("Word 正文结构无法读取。") from exc
    body = root.find(".//" + W + "body")
    if body is None:
        raise ValueError("Word 文档没有正文内容。")
    lines = []
    for paragraph in _body_paragraphs(body):
        lines.extend(part.strip() for part in paragraph.splitlines() if part.strip())
    return lines


def _parse_lines(lines, title):
    questions = []
    answer_key = {}
    shared_material = []
    collecting_material = False
    reading_answer_key = False
    current = None

    def finish_question():
        if current is not None:
            questions.append(current)

    for line in lines:
        line = line.strip()
        if not line:
            continue

        material_match = _MATERIAL_START.match(line)
        if material_match:
            finish_question()
            current = None
            shared_material = []
            collecting_material = True
            reading_answer_key = False
            if material_match.group(1).strip():
                shared_material.append(material_match.group(1).strip())
            continue
        if line in ("【材料结束】", "【阅读材料结束】"):
            finish_question()
            current = None
            shared_material = []
            collecting_material = False
            continue

        answer_section = re.match(
            r"^【?\s*(参考答案|答案汇总|答案表|答案)\s*】?\s*[:：]?\s*(.*)$", line)
        if answer_section:
            label, answer_text = answer_section.groups()
            answer_pairs = _ANSWER_PAIRS.findall(answer_text)
            single_answer = _ANSWER.match(line)
            if label == "答案" and single_answer and current is not None:
                current["correct_letter"] = _letter(single_answer.group(1))
                continue
            if label == "答案" and not answer_pairs and answer_text.strip() and answer_text.strip() in "ABCDＡＢＣＤ":
                continue
            finish_question()
            current = None
            collecting_material = False
            reading_answer_key = True
            for number, letter in answer_pairs:
                answer_key[int(number)] = _letter(letter)
            continue
        if reading_answer_key:
            for number, letter in _ANSWER_PAIRS.findall(line):
                answer_key[int(number)] = _letter(letter)
            continue

        question_match = _QUESTION.match(line)
        if question_match:
            finish_question()
            collecting_material = False
            reading_answer_key = False
            number = int(question_match.group("num") or question_match.group("num2"))
            stem = question_match.group("text") or question_match.group("text2") or ""
            current = {
                "number": number,
                "text_parts": [],
                "material_parts": list(shared_material),
                "answers": ["", "", "", ""],
                "correct_letter": None,
                "options_started": False,
            }
            if stem.strip():
                current["text_parts"].append(stem.strip())
            continue

        per_question_answer = _ANSWER.match(line)
        if per_question_answer and current is not None:
            current["correct_letter"] = _letter(per_question_answer.group(1))
            continue

        option_match = _OPTION.match(line)
        if option_match and current is not None:
            letter = _letter(option_match.group(1) or option_match.group(2))
            current["answers"][ord(letter) - ord("A")] = option_match.group(3).strip()
            current["options_started"] = True
            continue

        if current is not None:
            if not current["options_started"]:
                current["text_parts"].append(line)
        elif collecting_material:
            shared_material.append(line)

    finish_question()
    if not questions:
        raise ValueError("没有识别到题目。请按模板使用“1.题干”和 A、B、C、D 分行标注选项。")

    output = []
    missing_answers = 0
    for question in questions:
        number = question["number"]
        options = question["answers"]
        missing_options = ["ABCD"[index] for index, value in enumerate(options) if not value]
        if missing_options:
            raise ValueError(f"第 {number} 题缺少选项 {', '.join(missing_options)}，请补齐 A、B、C、D。")
        correct_letter = question["correct_letter"] or answer_key.get(number)
        correct = (ord(correct_letter) - ord("A")
                   if isinstance(correct_letter, str) and correct_letter in "ABCD" else -1)
        if correct < 0:
            missing_answers += 1
        text = "\n".join(part for part in question["text_parts"] if part).strip()
        if not text:
            raise ValueError(f"第 {number} 题没有识别到题干。")
        output.append({
            "text": text,
            "material": "\n".join(question["material_parts"]),
            "source_number": number,
            "answers": options,
            "correct": correct,
            "time": 20,
            "points": 1000,
            "media": None,
        })

    return {
        "title": title or "语文测验",
        "settings": {
            "default_time": 20,
            "default_points": 1000,
            "shuffle_questions": False,
            "shuffle_answers": False,
            "show_distribution": True,
            "auto_reveal_s": 6,
            "auto_gap_s": 3,
        },
        "questions": output,
        "missing_answers": missing_answers,
    }


def parse_docx_quiz_upload(filename, content_base64):
    """Return a quiz draft without saving it to the quiz bank."""
    filename = os.path.basename(str(filename or ""))
    if not filename.lower().endswith(".docx"):
        raise ValueError("请上传 .docx 格式的 Word 文档。")
    if not isinstance(content_base64, str) or not content_base64:
        raise ValueError("没有收到 Word 文件内容。")
    try:
        blob = base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Word 文件编码无效。") from exc
    if len(blob) > MAX_DOCX_BYTES:
        raise ValueError("DOCX 文件不能超过 8 MB。")
    stem = os.path.splitext(filename)[0].strip() or "语文测验"
    quiz = _parse_lines(_read_docx(blob), stem)
    missing_answers = quiz.pop("missing_answers")
    return {"quiz": quiz, "question_count": len(quiz["questions"]),
            "missing_answers": missing_answers}
