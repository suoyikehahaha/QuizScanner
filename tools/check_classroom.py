"""Disposable regression checks for scoring, classes, restart and stale events."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quizscanner.session import QuizSession
from quizscanner import report
from quizscanner.storage import write_json

quiz = {"title": "语文课堂核验", "questions": [
    {"text": "题一", "answers": ["甲", "乙", "丙", "丁"], "correct": 0, "points": 100, "time": 0},
    {"text": "题二", "answers": ["甲", "乙", "丙", "丁"], "correct": 1, "points": 100, "time": 0},
]}
roster = {"version": 2, "active_class": "甲班", "classes": ["甲班", "乙班", "空班"], "students": [
    {"class_name": "甲班", "student_no": "1801", "name": "甲同学", "card_id": 0},
    {"class_name": "甲班", "student_no": "1802", "name": "未扫码同学", "card_id": 1},
    {"class_name": "乙班", "student_no": "2301", "name": "乙同学", "card_id": 0},
]}
s = QuizSession(); s.set_roster(roster); s.load_quiz(quiz, "核验")
s.start_question(); first = s.attempt_id
assert not s.record_answers({0: "A"}, attempt_id="expired")
assert s.record_answers({0: "A"}, attempt_id=first, event_id="one")
s.end_question(); assert s.leaderboard()[0]["score"] == 100
s.goto(0); s.start_question(); s.record_answers({0: "A"}); s.end_question()
assert s.leaderboard()[0]["score"] == 100
s.goto(0); s.start_question(); s.record_answers({0: "B"}); s.end_question()
assert s.leaderboard()[0]["score"] == 0
assert len(s.history) == 3
s.goto(0); s.start_question(); s.record_answers({0: "A"}); s.end_question()
s.set_active_class("乙班"); s.goto(0); s.start_question(); s.record_answers({0: "A"}); s.end_question()
for class_name in ("甲班", "乙班"):
    r = report.build(s, class_name=class_name)
    answered = [student for student in r["students"] if student["answered"]]
    assert len(answered) == 1 and answered[0]["score"] == 100
    assert r["questions"][0]["answered"] == 1
assert len(report.build(s, class_name="甲班")["students"]) == 2
s.set_active_class("空班")
try: s.start_question(); raise AssertionError("empty class accepted")
except ValueError: pass
s.set_active_class("甲班"); s.goto(0); s.start_question()
attempt = s.attempt_id; s.record_answers({0: "A", 88: "D"})
assert s.state(full=True)["answered"] == 1
assert s.move_and_start("next") and s.index == 1 and s.phase == "question" and s.attempt_id != attempt
assert not s.record_answers({0: "A"}, attempt_id=attempt)
s.record_answers({0: "B"}); s.end_question()
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)/"classroom.json"
    write_json(str(path), s.snapshot())
    restored = QuizSession(); restored.restore(json.loads(path.read_text(encoding="utf-8")))
    assert restored.scores == s.scores and restored.history == s.history
    assert restored.active_class == s.active_class
    assert len(restored.roster) == 2
    assert report.build(restored)["summary"]["questions"] == 2
print("PASS: 重答替换、错误重答扣回、跨班隔离、未扫码名单、空班拒收、过期事件、同步切题、持久恢复")
