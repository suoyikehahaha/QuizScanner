"""Exercise the local native protocol using only disposable classroom data."""
import os
import sys
import json
import tempfile
import threading
import urllib.request
import urllib.error
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

with tempfile.TemporaryDirectory() as directory:
    os.environ["QUIZSCANNER_DATA_DIR"] = directory
    from quizscanner import server
    from quizscanner.storage import write_json
    from quizscanner.session import QuizSession
    import cv2
    import numpy as np
    quiz = {"title": "API fixture", "questions": [
        {"text": "one", "answers": ["a", "b", "c", "d"], "correct": 0, "points": 100, "time": 0},
        {"text": "two", "answers": ["a", "b", "c", "d"], "correct": 1, "points": 100, "time": 0}]}
    roster = {"version": 2, "active_class": "A", "classes": ["A"], "students": [
        {"student_no": "1801", "name": "Student A", "class_name": "A", "card_id": 0},
        {"student_no": "1802", "name": "Student B", "class_name": "A", "card_id": 1}]}
    write_json(str(Path(directory)/"quizzes"/"fixture.json"), quiz)
    write_json(str(Path(directory)/"roster.json"), roster)
    httpd = server.build_server(port=8130 if "--serve" in sys.argv else 0, host="127.0.0.1", no_camera=True)
    if "--serve" in sys.argv:
        print("UI_CHECK_READY: http://127.0.0.1:8130", flush=True)
        try: httpd.serve_forever()
        except KeyboardInterrupt: pass
        finally: server.session.stop_auto_engine(); httpd.server_close()
        sys.exit(0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_port}"
    def call(path, body=None):
        request = urllib.request.Request(base+path, data=json.dumps(body).encode() if body is not None else None,
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.load(response)
    try:
        assert call("/api/meta")["native_protocol"] == 1
        started = call("/api/control", {"action": "start", "command_id": "start-once"})["state"]
        assert call("/api/control", {"action": "start", "command_id": "start-once"})["state"]["attempt_id"] == started["attempt_id"]
        event = {"session_id": started["session_id"], "class_name": "A", "attempt_id": started["attempt_id"], "event_id": "answer-once", "answers": {"0": "A"}}
        assert call("/api/native/answers", event)["ok"]
        assert call("/api/native/answers", event)["ok"]
        assert call("/api/control", {"action": "end"})["state"]["phase"] == "ended"
        preview = call("/api/report/preview")
        assert preview["summary"]["students"] == 2 and preview["questions"][0]["answered"] == 1
        next_state = call("/api/control", {"action": "next_start"})["state"]
        assert next_state["index"] == 1 and next_state["phase"] == "question"
        try: call("/api/native/answers", event); raise AssertionError("stale event")
        except urllib.error.HTTPError as error: assert error.code == 409
        png = urllib.request.urlopen(base+"/api/connect.png?address=127.0.0.1").read()
        image = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_GRAYSCALE)
        payload = cv2.QRCodeDetector().detectAndDecode(image)[0]
        assert payload.startswith("quizscanner://connect?") and "code=" in payload
        paired = call("/api/native/pair", {"code": server._pair_code})
        fake = server.Handler.__new__(server.Handler)
        fake.client_address = ("192.168.1.250", 1)
        fake.headers = {}; assert not fake.authorized()
        fake.headers = {"X-Teacher-Token": paired["token"]}; assert fake.authorized()
        saved_roster = call("/api/roster")["students"]
        offline = {"id": "a"*32, "class_name": "A", "quiz_name": "fixture", "quiz": quiz,
                   "roster": saved_roster, "history": [{"index": 0, "answers": {"0": "A"}}]}
        assert call("/api/native/import", offline)["ok"]
        assert call("/api/native/import", offline)["already_imported"]
        assert call("/api/report/preview?session="+"a"*32)["questions"][0]["answered"] == 1
        assert server.session.index == 1 and server.session.phase == "question"
        assert Path(directory, "classroom.json").exists()
        restored = QuizSession(); restored.restore(json.loads(Path(directory, "classroom.json").read_text(encoding="utf-8")))
        assert restored.index == 1 and restored.attempt_id == server.session.attempt_id
        print("PASS: native protocol, command dedup, stale answer rejection, QR decode, pairing, offline import, report isolation, recovery")
    finally:
        server.stop_server(httpd); httpd.server_close()
