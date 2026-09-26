"""Parse teacher roster uploads from UTF-8/GBK CSV or an XLSX workbook."""

import base64
import csv
import io
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET


MAX_UPLOAD_BYTES = 3 * 1024 * 1024
MAX_WORKBOOK_EXPANDED_BYTES = 16 * 1024 * 1024
MAX_STUDENTS_PER_CLASS = 250  # DICT_4X4_250 has marker IDs 0..249.
MAX_ROSTER_STUDENTS = 25000
DEFAULT_CLASS_NAME = "未分班"


def _decode_csv(raw):
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("gbk")
        except UnicodeDecodeError as exc:
            raise ValueError("CSV 文件编码无法识别，请另存为 UTF-8 CSV。") from exc

    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return list(csv.reader(io.StringIO(text), dialect))


def _xlsx_rows(raw):
    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    package_rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    ns = {"m": main_ns, "r": rel_ns, "p": package_rel_ns}

    try:
        book = zipfile.ZipFile(io.BytesIO(raw))
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError("无法读取 XLSX 文件，请用 Excel 重新保存后再上传。") from exc

    with book:
        infos = book.infolist()
        if sum(info.file_size for info in infos) > MAX_WORKBOOK_EXPANDED_BYTES:
            raise ValueError("XLSX 解压后文件过大，无法导入。")
        names = set(book.namelist())
        if "xl/workbook.xml" not in names:
            raise ValueError("XLSX 文件中没有工作簿内容。")

        workbook = ET.fromstring(book.read("xl/workbook.xml"))
        sheet = workbook.find("m:sheets/m:sheet", ns)
        if sheet is None:
            raise ValueError("XLSX 工作簿中没有工作表。")
        rel_id = sheet.get(f"{{{rel_ns}}}id")

        sheet_path = None
        rels_path = "xl/_rels/workbook.xml.rels"
        if rels_path in names and rel_id:
            rels = ET.fromstring(book.read(rels_path))
            for rel in rels.findall("p:Relationship", ns):
                if rel.get("Id") == rel_id:
                    target = rel.get("Target", "")
                    sheet_path = (target.lstrip("/") if target.startswith("/")
                                  else posixpath.normpath(posixpath.join("xl", target)))
                    break
        if not sheet_path or sheet_path not in names:
            if "xl/worksheets/sheet1.xml" in names:
                sheet_path = "xl/worksheets/sheet1.xml"
            else:
                raise ValueError("无法找到 XLSX 中的第一个工作表。")

        shared = []
        if "xl/sharedStrings.xml" in names:
            strings = ET.fromstring(book.read("xl/sharedStrings.xml"))
            for item in strings.findall("m:si", ns):
                shared.append("".join(node.text or "" for node in item.findall(".//m:t", ns)))

        sheet_xml = ET.fromstring(book.read(sheet_path))
        sheet_data = sheet_xml.find(".//m:sheetData", ns)
        if sheet_data is None:
            return []

        rows = []
        for row in sheet_data.findall("m:row", ns):
            values = {}
            fallback_col = 0
            for cell in row.findall("m:c", ns):
                ref = cell.get("r", "")
                match = re.match(r"([A-Z]+)", ref, re.I)
                if match:
                    col = 0
                    for char in match.group(1).upper():
                        col = col * 26 + ord(char) - ord("A") + 1
                    col -= 1
                else:
                    col = fallback_col
                fallback_col = col + 1

                cell_type = cell.get("t")
                if cell_type == "inlineStr":
                    value = "".join(node.text or "" for node in cell.findall(".//m:t", ns))
                else:
                    value_node = cell.find("m:v", ns)
                    value = value_node.text if value_node is not None else ""
                    if cell_type == "s" and value:
                        try:
                            value = shared[int(value)]
                        except (ValueError, IndexError):
                            raise ValueError("XLSX 中的共享文本索引无效。")
                values[col] = value

            if values:
                rows.append([values.get(index, "") for index in range(max(values) + 1)])
            else:
                rows.append([])
        return rows


def _normalise_header(value):
    return re.sub(r"[\s_\-#]+", "", str(value or "").strip().casefold())


def _natural_key(value):
    """按数字片段自然排序，保证 1801、1802、1810 的顺序可读。"""
    parts = re.split(r"(\d+)", str(value or "").strip().casefold())
    return tuple((0, int(part)) if part.isdigit() else (1, part) for part in parts)


def student_number_sort_key(value):
    """公开学号自然排序键，供实时名单与成绩报告保持同一顺序。"""
    return _natural_key(value)


def _sort_students(students):
    return sorted(students, key=lambda student: (
        _natural_key(student["class_name"]),
        _natural_key(student["student_no"]),
        student["name"].casefold(),
    ))


def _normalise_roster(data):
    """将新版班级名单或旧版 {卡片编号: 姓名} 转为统一结构。"""
    active_class = None
    declared_classes = []
    if isinstance(data, dict) and isinstance(data.get("students"), list):
        active_class = str(data.get("active_class") or "").strip() or None
        raw_students = data["students"]
        raw_classes = data.get("classes", [])
        if isinstance(raw_classes, (list, tuple)):
            declared_classes = list(dict.fromkeys(
                str(class_name).strip() for class_name in raw_classes
                if str(class_name or "").strip()
            ))
    elif isinstance(data, dict):
        # 兼容旧版 roster.json 与旧页面提交的字典格式。
        raw_students = []
        for raw_id, name in data.items():
            try:
                marker_id = int(raw_id)
            except (ValueError, TypeError):
                continue
            raw_students.append({
                "class_name": DEFAULT_CLASS_NAME,
                "student_no": str(raw_id),
                "name": str(name or "").strip(),
                "card_id": marker_id,
            })
    else:
        raw_students = []

    students = []
    for row in raw_students:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        class_name = str(row.get("class_name") or row.get("class") or DEFAULT_CLASS_NAME).strip()
        class_name = class_name or DEFAULT_CLASS_NAME
        student_no = str(row.get("student_no") or row.get("school_no") or row.get("id") or "").strip()
        if not student_no:
            student_no = str(len(students) + 1)
        raw_card_id = row.get("card_id", row.get("marker_id"))
        card_id = None
        if raw_card_id not in (None, ""):
            try:
                card_id = int(raw_card_id)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"学号 {student_no} 的答题卡编号不是整数。") from exc
        students.append({
            "class_name": class_name,
            "student_no": student_no,
            "name": name,
            "card_id": card_id,
        })

    students = _sort_students(students)
    if len(students) > MAX_ROSTER_STUDENTS:
        raise ValueError(f"名单总人数不能超过 {MAX_ROSTER_STUDENTS} 人。")

    by_class = {}
    school_ids = set()
    for student in students:
        class_name = student["class_name"]
        class_ids = by_class.setdefault(class_name, set())
        if len(class_ids) >= MAX_STUDENTS_PER_CLASS:
            raise ValueError(f"{class_name} 超过 250 人，无法使用当前答题卡字典。")
        identity = (class_name, student["student_no"])
        if identity in school_ids:
            raise ValueError(f"{class_name} 中学号 {student['student_no']} 重复。")
        school_ids.add(identity)
        card_id = student["card_id"]
        if card_id is not None:
            if not 0 <= card_id < MAX_STUDENTS_PER_CLASS:
                raise ValueError(f"{class_name} 中学号 {student['student_no']} 的卡片编号须为 0–249。")
            if card_id in class_ids:
                raise ValueError(f"{class_name} 中答题卡编号 {card_id} 重复。")
            class_ids.add(card_id)

    # 卡片标记编号只在班级内部唯一。它与学号分开保存，避免学号 1801
    # 被改写为内部卡号 0；卡片顺序和抬头仍使用原学号。
    by_class.clear()
    for student in students:
        by_class.setdefault(student["class_name"], []).append(student)
    for class_name, group in by_class.items():
        used = {student["card_id"] for student in group if student["card_id"] is not None}
        for student in group:
            if student["card_id"] is not None:
                continue
            marker_id = next((candidate for candidate in range(MAX_STUDENTS_PER_CLASS)
                              if candidate not in used), None)
            if marker_id is None:
                raise ValueError(f"{class_name} 没有可分配的答题卡编号。")
            student["card_id"] = marker_id
            used.add(marker_id)

    # 班级可以先于学生创建，因此保留 roster.json 中只有班名、没有学生的空班级。
    classes = sorted(set(declared_classes).union(by_class), key=_natural_key)
    if active_class not in classes:
        active_class = classes[0] if classes else ""
    return {
        "version": 2,
        "classes": classes,
        "active_class": active_class,
        "students": students,
    }


def normalise_roster(data):
    """公开统一名单结构化入口，供导入、迁移和保存共用。"""
    return _normalise_roster(data)


def _make_roster(rows, default_class_name=None):
    default_class_name = str(default_class_name or DEFAULT_CLASS_NAME).strip() or DEFAULT_CLASS_NAME
    rows = [[str(value or "").strip() for value in row] for row in rows]
    rows = [row for row in rows if any(row)]
    if not rows:
        raise ValueError("名单文件中没有学生数据。")

    # 学号是学校使用的学生编号；卡片编号是 ArUco 字典中的内部编号，
    # 两者分开读取。卡片编号可在不同班级中重复。
    student_no_headers = {"id", "编号", "学号", "学生学号", "序号", "number", "no",
                          "studentid", "studentno", "studentnumber"}
    card_id_headers = {"卡片编号", "答题卡编号", "卡片号", "标记编号", "aruco编号",
                       "cardid", "markerid", "arucoid"}
    name_headers = {"name", "fullname", "student", "studentname", "姓名", "学生", "学生姓名"}
    class_headers = {"class", "classname", "班级", "行政班", "教学班", "班别"}
    header = [_normalise_header(value) for value in rows[0]]
    student_no_col = next((i for i, value in enumerate(header) if value in student_no_headers), None)
    card_id_col = next((i for i, value in enumerate(header) if value in card_id_headers), None)
    name_col = next((i for i, value in enumerate(header) if value in name_headers), None)
    class_col = next((i for i, value in enumerate(header) if value in class_headers), None)

    if name_col is not None:
        start_row = 1
    elif student_no_col is not None or class_col is not None:
        raise ValueError("名单表没有识别到姓名列，请使用“学号”“姓名”“班级”作为列名。")
    else:
        start_row = 0
        if len(rows[0]) >= 2 and rows[0][0].isdigit():
            student_no_col, name_col = 0, 1
            class_col = 2 if len(rows[0]) >= 3 else None
        else:
            student_no_col, name_col = None, 0
            class_col = 1 if len(rows[0]) >= 2 else None

    students = []
    for row_number, row in enumerate(rows[start_row:], start=start_row + 1):
        name = row[name_col].strip() if name_col < len(row) else ""
        if not name:
            continue
        raw_no = row[student_no_col].strip() if student_no_col is not None and student_no_col < len(row) else ""
        student_no = raw_no or str(row_number - start_row)
        class_name = row[class_col].strip() if class_col is not None and class_col < len(row) else ""
        raw_card_id = row[card_id_col].strip() if card_id_col is not None and card_id_col < len(row) else ""
        students.append({
            "student_no": student_no,
            "name": name,
            "class_name": class_name or default_class_name,
            "card_id": raw_card_id or None,
        })

    if not students:
        raise ValueError("没有找到有效的学生姓名。请检查表格列名和内容。")
    return normalise_roster({"students": students})


def parse_roster_upload(filename, content_base64, default_class_name=None):
    """解析名单；无班级列或班级单元格为空时使用所选班级。"""
    extension = str(filename or "").lower().rsplit(".", 1)
    extension = "." + extension[-1] if len(extension) == 2 else ""
    if extension not in {".csv", ".xlsx"}:
        raise ValueError("目前支持 CSV 或 XLSX 名单文件。")
    try:
        raw = base64.b64decode(content_base64 or "", validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("上传文件数据无效，请重新选择文件。") from exc
    if not raw:
        raise ValueError("上传文件为空。")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("名单文件不能超过 3 MB。")

    if extension == ".csv":
        rows = _decode_csv(raw)
    else:
        try:
            rows = _xlsx_rows(raw)
        except (zipfile.BadZipFile, ET.ParseError, KeyError, OSError) as exc:
            raise ValueError("XLSX 文件内容损坏或格式不受支持，请用 Excel 重新保存。") from exc
    return _make_roster(rows, default_class_name=default_class_name)
