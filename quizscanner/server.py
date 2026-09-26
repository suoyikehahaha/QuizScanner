"""
Serwer aplikacji QuizScanner (biblioteka standardowa Pythona, bez Flask).

Uruchamia:
  - wątek kamery (skaner ArUco),
  - serwer HTTP z panelem nauczyciela, tablica i edytorem.

Użycie:
  python -m quizscanner                 # kamera 0, port 8000, otwiera przeglądarkę
  python -m quizscanner --camera 1 --port 8000 --no-browser

Adresy:
  Panel nauczyciela : http://localhost:PORT/teacher
  Tablica (rzutnik) : http://localhost:PORT/board
  Edytor pytań      : http://localhost:PORT/editor
  Tablica w sieci   : http://<IP-w-LAN>:PORT/board
"""

import argparse
import ipaddress
import json
import os
import re
import socket
import secrets
import subprocess
import sys
import threading
import time
import webbrowser
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote, urlencode

from .storage import write_json
from . import VERSION
from . import report as report_mod
from . import updater
from .paths import (DATA_DIR, MEDIA_DIR, QUIZ_DIR, REPORT_DIR, ROSTER_JSON,
                    SETTINGS_JSON, STUDENTS_CSV, WEB_DIR, seed_data)
from .session import QuizSession, PHASE_IDLE
from .camera import CameraScanner
from .roster_import import (DEFAULT_CLASS_NAME, normalise_roster,
                            parse_roster_upload)
from .docx_import import parse_docx_quiz_upload

# Ustawienia aplikacji (zapisywane w folderze danych).
DEFAULT_SETTINGS = {
    "lang": "zh",          # interface language: zh / pl / en
    "camera": "0",         # numer kamery albo adres strumienia (telefon)
    "mirror": True,        # lustro w podglądzie (nie wpływa na rozpoznawanie)
    "only_known": True,    # akceptuj tylko ID z listy uczniów
    "theme": "light",      # jasny motyw interfejsu i tła projekcji
    "sound": False,        # projection effects disabled
    "volume": 0.6,         # głośność dźwięków (0..1)
    "countdown_enabled": True,
    "scan_visibility": "status",  # status (anonymous) or answer during scanning
    "show_student_answers_on_reveal": True,
    "auto_report": True,   # zapisuj raport automatycznie po zakończeniu quizu
    "check_updates": False, # localized fork updates remain opt-in
}
settings = dict(DEFAULT_SETTINGS)
_LAN_IP_CACHE = {"at": 0.0, "addresses": []}


def load_settings():
    global settings
    data = dict(DEFAULT_SETTINGS)
    try:
        if os.path.exists(SETTINGS_JSON):
            with open(SETTINGS_JSON, encoding="utf-8") as f:
                data.update(json.load(f))
    except Exception:
        pass
    data["sound"] = False
    data["countdown_enabled"] = bool(data.get("countdown_enabled", True))
    data["scan_visibility"] = "status" if data.get("scan_visibility") == "status" else "answer"
    data["show_student_answers_on_reveal"] = bool(
        data.get("show_student_answers_on_reveal", True)
    )
    settings = data
    return settings


def save_settings():
    try:
        write_json(SETTINGS_JSON, settings)
    except Exception:
        pass


session = QuizSession()
_state_changed = threading.Event()
_command_ids = {}
_pair_code = str(secrets.randbelow(900000) + 100000)
_pair_token = secrets.token_urlsafe(32)
_pair_attempts = {}
_native_seen = 0.0


def checkpoint(current):
    if not current.quiz_name:
        return
    snapshot = current.snapshot()
    write_json(os.path.join(DATA_DIR, "sessions", current.session_id + ".json"), snapshot)
    write_json(os.path.join(DATA_DIR, "classroom.json"), snapshot)
    _state_changed.set()

scanner = None       # ustawiany przy starcie serwera
pending_swap = None  # skrypt podmiany pliku po pobraniu aktualizacji

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp",
    ".mp4": "video/mp4", ".webm": "video/webm", ".ogg": "video/ogg",
    # Czcionki KaTeX (web/vendor/katex/fonts).
    ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf",
}

# Dozwolone typy plików dodawanych do pytań.
MEDIA_EXT = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
    "image/webp": ".webp",
    "video/mp4": ".mp4", "video/webm": ".webm",
}
MEDIA_MAX_MB = 40


# --------------------------- pomocnicze ---------------------------
def safe_name(name):
    """Sanitizes a quiz filename while preserving Unicode letters."""
    value = str(name or "").replace("/", " ").replace("\\", " ")
    return re.sub(r"[^\w\- ]", "", value, flags=re.UNICODE).strip() or "quiz"


def list_quizzes():
    if not os.path.isdir(QUIZ_DIR):
        return []
    out = []
    for f in sorted(os.listdir(QUIZ_DIR)):
        if f.endswith(".json"):
            out.append(f[:-5])
    return out


def read_quiz(name):
    path = os.path.join(QUIZ_DIR, safe_name(name) + ".json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_quiz(name, quiz):
    os.makedirs(QUIZ_DIR, exist_ok=True)
    path = os.path.join(QUIZ_DIR, safe_name(name) + ".json")
    write_json(path, quiz)


def delete_quiz(name):
    path = os.path.join(QUIZ_DIR, safe_name(name) + ".json")
    if os.path.exists(path):
        os.remove(path)


def load_roster():
    """读取并迁移班级名单；旧版 {卡片编号: 姓名} 会映射到未分班。"""
    if os.path.exists(ROSTER_JSON):
        with open(ROSTER_JSON, encoding="utf-8") as f:
            data = json.load(f)
        return normalise_roster(data)
    if os.path.exists(STUDENTS_CSV):
        import base64
        with open(STUDENTS_CSV, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        try:
            return parse_roster_upload("students.csv", encoded)
        except ValueError:
            pass
    return normalise_roster({})


def save_roster(roster):
    roster = normalise_roster(roster)
    write_json(ROSTER_JSON, roster)
    return roster


def placeholder_jpeg(text):
    """Statyczny kadr JPEG (gdy nie ma kamery)."""
    import io
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (640, 360), (34, 34, 40))
    d = ImageDraw.Draw(img)
    d.text((210, 168), text, fill=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


def lan_ips():
    """返回可供手机访问的本机私有 IPv4，热点地址优先。"""
    now = time.monotonic()
    if now - _LAN_IP_CACHE["at"] < 5:
        return list(_LAN_IP_CACHE["addresses"])
    private_networks = (
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
    )

    def is_private_lan(address):
        try:
            parsed = ipaddress.ip_address(address)
            return parsed.version == 4 and any(parsed in network for network in private_networks)
        except ValueError:
            return False

    addresses = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            route_address = s.getsockname()[0]
            if is_private_lan(route_address):
                addresses.add(route_address)
    except Exception:
        route_address = None

    # 获取 Wi-Fi/以太网/Windows 移动热点地址；跳过代理和 TUN 非私有地址。
    try:
        addresses.update({
            info[4][0]
            for info in socket.getaddrinfo(socket.gethostname(), None,
                                           socket.AF_INET, socket.SOCK_DGRAM)
            if is_private_lan(info[4][0])
        })
    except OSError:
        pass
    if os.name == "nt":
        # Windows 移动热点虚拟网卡地址不一定出现在 hostname DNS 查询结果里。
        try:
            process_options = {}
            if os.name == "nt":
                process_options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            result = subprocess.run(
                ["ipconfig"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                timeout=2, check=False, **process_options,
            )
            output = result.stdout.decode("latin-1", errors="ignore")
            addresses.update(address for address in
                             re.findall(r"(?im)^.*IPv4[^:\r\n]*:\s*((?:\d{1,3}\.){3}\d{1,3})", output)
                             if is_private_lan(address))
        except (OSError, subprocess.TimeoutExpired):
            pass

    def priority(address):
        if address.startswith("192.168.137."):
            return (0, address)
        if address == route_address:
            return (1, address)
        if address.startswith("192.168."):
            return (2, address)
        if address.startswith("10."):
            return (3, address)
        return (4, address)

    ordered = sorted(addresses, key=priority)
    _LAN_IP_CACHE.update({"at": now, "addresses": ordered})
    return ordered


def lan_ip():
    """优先返回电脑热点地址，便于手机在热点下连接。"""
    addresses = lan_ips()
    return addresses[0] if addresses else "127.0.0.1"


def export_quiz_bundle(quiz):
    """Buduje samodzielny plik .quiz -- z osadzonymi mediami (base64),
    żeby dało się go wysłać innemu nauczycielowi jako jeden plik."""
    import base64
    bundle = json.loads(json.dumps(quiz))  # kopia
    bundle["format"] = "quizscanner/1"
    media = {}
    for q in bundle.get("questions", []):
        m = q.get("media")
        if not m or not m.get("file"):
            continue
        p = os.path.join(MEDIA_DIR, os.path.basename(m["file"]))
        if os.path.exists(p) and os.path.getsize(p) <= MEDIA_MAX_MB * 1024 * 1024:
            with open(p, "rb") as f:
                media[m["file"]] = base64.b64encode(f.read()).decode("ascii")
    if media:
        bundle["media_data"] = media
    return json.dumps(bundle, ensure_ascii=False, indent=2)


def import_quiz_bundle(bundle):
    """Odwrotność export_quiz_bundle: zapisuje media na dysk i zwraca quiz."""
    import base64
    quiz = json.loads(json.dumps(bundle))
    blobs = quiz.pop("media_data", None) or {}
    quiz.pop("format", None)
    if blobs:
        os.makedirs(MEDIA_DIR, exist_ok=True)
        for fname, b64 in blobs.items():
            safe = os.path.basename(str(fname))
            ext = os.path.splitext(safe)[1].lower()
            if ext not in set(MEDIA_EXT.values()):
                continue
            try:
                data = base64.b64decode(b64)
            except Exception:
                continue
            if len(data) > MEDIA_MAX_MB * 1024 * 1024:
                continue
            with open(os.path.join(MEDIA_DIR, safe), "wb") as f:
                f.write(data)
    return quiz


def save_media(data_url, orig_name=""):
    """Zapisuje plik przesłany jako data:URL. Zwraca (nazwa, typ) albo błąd."""
    import base64
    import hashlib
    if not data_url.startswith("data:"):
        raise ValueError("bad payload")
    head, _, b64 = data_url.partition(",")
    mime = head[5:].split(";")[0].strip().lower()
    ext = MEDIA_EXT.get(mime)
    if not ext:
        raise ValueError("unsupported type")
    raw = base64.b64decode(b64)
    if len(raw) > MEDIA_MAX_MB * 1024 * 1024:
        raise ValueError("too large")
    os.makedirs(MEDIA_DIR, exist_ok=True)
    digest = hashlib.sha1(raw).hexdigest()[:16]
    fname = digest + ext
    with open(os.path.join(MEDIA_DIR, fname), "wb") as f:
        f.write(raw)
    kind = "video" if mime.startswith("video/") else "image"
    return fname, kind


def build_cards_pdf(count=None, class_name=None, paper="a4"):
    """Tworzy w pamięci PDF z kartami ArUco (jedna karta na stronę A4).
    Domyślnie karty dla aktualnej listy uczniów; jeśli lista pusta lub podano
    count -- karty o numerach 0..count-1."""
    import io
    import cv2
    from PIL import Image
    from .aruco import get_dictionary
    from .cards import make_card

    dictionary = get_dictionary()
    roster_data = load_roster()
    selected_class = class_name or roster_data.get("active_class", "")
    students = [student for student in roster_data.get("students", [])
                if student.get("class_name") == selected_class]
    if students and not count:
        card_rows = students
    else:
        card_rows = [{"card_id": mid, "student_no": str(mid),
                      "class_name": selected_class or DEFAULT_CLASS_NAME,
                      "name": ""}
                     for mid in range(count or 30)]

    W, H = (1165, 1653) if paper == "a5" else (1654, 2339)  # 200 DPI
    marker_px = int(min(W, H) * 0.55)
    pages = []
    for student in card_rows:
        mid = int(student["card_id"])
        card = make_card(
            mid, student.get("name", ""), dictionary, (W, H), marker_px,
            lang=settings.get("lang", "zh"),
            student_no=student.get("student_no"),
            class_name=student.get("class_name"),
        )
        pages.append(Image.fromarray(cv2.cvtColor(card, cv2.COLOR_BGR2RGB)))

    buf = io.BytesIO()
    if pages:
        pages[0].save(buf, format="PDF", save_all=True,
                      append_images=pages[1:], resolution=200.0)
    return buf.getvalue()


AUTOSAVE_FORMATS = ("html", "csv", "json")


def save_report(formats=AUTOSAVE_FORMATS):
    """Zapisuje raport z bieżącej rozgrywki do folderu raportów."""
    return report_mod.save(
        report_mod.build(session, lang=settings.get("lang", "zh")), REPORT_DIR, formats)


def autosave_report(_session=None):
    """Wywoływane automatycznie, gdy quiz dobiegnie końca (podium)."""
    if not settings.get("auto_report", True):
        return []
    with session.lock:
        if not session.history:
            return []          # nic nie rozegrano -- nie ma czego zapisywać
    return save_report()


def report_session(query):
    sid = query.get("session", [None])[0]
    if not sid:
        return session
    if not re.fullmatch(r"[a-f0-9]{32}", sid):
        raise ValueError("课堂编号无效")
    result = QuizSession()
    with open(os.path.join(DATA_DIR, "sessions", sid + ".json"), encoding="utf-8") as stream:
        result.restore(json.load(stream))
    return result


# --------------------------- handler ---------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "QuizScanner"
    # HTTP/1.1 = trwałe połączenia. Bez tego każde zapytanie zrywa połączenie,
    # co bardzo spowalnia odpytywanie stanu przez panel i tablice.
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass  # cisza w konsoli

    # ---- odpowiedzi ----
    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if self.path == "/api/native/pair" and code == 200 and obj.get("token"):
            self.send_header("Set-Cookie", f"qs_teacher_token={obj['token']}; HttpOnly; SameSite=Strict; Path=/")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path):
        if not os.path.isfile(path):
            self.send_error(404, "Nie znaleziono")
            return
        ext = os.path.splitext(path)[1].lower()
        ctype = CONTENT_TYPES.get(ext, "application/octet-stream")
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    # ---- MJPEG ----
    def stream_mjpeg(self):
        if scanner is None:
            # Tryb bez kamery -- pojedynczy statyczny kadr zastępczy.
            jpg = placeholder_jpeg("Tryb bez kamery")
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(jpg)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(jpg)
            return
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store")
        # Strumień nie ma Content-Length -- musi zamykać połączenie na koniec.
        self.send_header("Connection", "close")
        self.close_connection = True
        self.end_headers()
        active_scanner = None
        last_sequence = 0
        try:
            while True:
                current_scanner = scanner
                if current_scanner is None:
                    time.sleep(0.1)
                    continue
                if current_scanner is not active_scanner:
                    active_scanner = current_scanner
                    last_sequence = 0
                sequence, jpg = active_scanner.get_jpeg_after(last_sequence, timeout=0.5)
                if jpg is None:
                    continue
                last_sequence = sequence
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(("Content-Length: %d\r\n\r\n" % len(jpg)).encode())
                self.wfile.write(jpg)
                self.wfile.write(b"\r\n")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def authorized(self):
        local = self.client_address[0] in ("127.0.0.1", "::1")
        supplied = self.headers.get("X-Teacher-Token", "")
        if not supplied:
            cookie = SimpleCookie()
            try:
                cookie.load(self.headers.get("Cookie", ""))
                supplied = cookie["qs_teacher_token"].value if "qs_teacher_token" in cookie else ""
            except Exception:
                supplied = ""
        return local or bool(supplied and secrets.compare_digest(supplied, _pair_token))

    # ---- GET ----
    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)

        public = path in ("/api/meta", "/api/state", "/api/presentation") and query.get("full", ["0"])[0] != "1"
        if path.startswith("/api/") and not public and not self.authorized():
            return self.send_json({"ok": False, "error": "请扫描电脑教师端的连接二维码完成配对。"}, code=401)
        if path == "/api/presentation":
            return self.send_json({key: settings.get(key) for key in
                                   ("theme", "lang", "sound", "scan_visibility", "show_student_answers_on_reveal")})
        if path == "/api/connect.png":
            import cv2
            import numpy as np
            address = query.get("address", [lan_ip()])[0]
            if address not in lan_ips() + ["127.0.0.1", "localhost"]:
                return self.send_json({"ok": False, "error": "该地址不属于本机"}, code=400)
            payload = "quizscanner://connect?" + urlencode({
                "url": f"http://{address}:{self.server.server_address[1]}", "code": _pair_code})
            code = cv2.QRCodeEncoder_create().encode(payload)
            code = np.pad(code, 4, constant_values=255)
            code = cv2.resize(code, (420, 420), interpolation=cv2.INTER_NEAREST)
            blob = cv2.imencode(".png", code)[1].tobytes()
            self.send_response(200); self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(blob))); self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(blob); return
        if path == "/":
            return self.redirect("/teacher")
        if path == "/teacher":
            return self.send_file(os.path.join(WEB_DIR, "teacher.html"))
        if path == "/mobile":
            return self.send_file(os.path.join(WEB_DIR, "mobile.html"))
        if path == "/board":
            return self.send_file(os.path.join(WEB_DIR, "board.html"))
        if path == "/editor":
            return self.send_file(os.path.join(WEB_DIR, "editor.html"))
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            rel = os.path.normpath(rel).replace("\\", "/")
            if rel.startswith(".."):
                return self.send_error(403)
            return self.send_file(os.path.join(WEB_DIR, rel))
        if path == "/video_feed":
            return self.stream_mjpeg()

        if path == "/api/report":
            fmt = (query.get("format", ["pdf"])[0] or "pdf").lower()
            try:
                blob, ctype, fname = report_mod.render(
                    report_mod.build(report_session(query), lang=settings.get("lang", "zh"), class_name=query.get("class", [None])[0]), fmt)
            except ValueError:
                return self.send_error(400, "未知的报告格式")
            except Exception as e:
                return self.send_error(500, f"生成报告失败：{e}")
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Disposition",
                             f'attachment; filename="{fname}"')
            self.send_header("Content-Length", str(len(blob)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(blob)
            return
        if path == "/api/report/preview":
            data = report_mod.build(report_session(query), lang=settings.get("lang", "zh"), class_name=query.get("class", [None])[0])
            return self.send_json({
                "summary": data["summary"], "questions": data["questions"],
                "students": data["students"], "quiz_title": data["quiz_title"],
                "formats": report_mod.FORMATS,
                "dir": REPORT_DIR,
                "saved": report_mod.list_saved(REPORT_DIR),
            })
        if path == "/api/update":
            force = query.get("force", ["0"])[0] == "1"
            if not settings.get("check_updates", True) and not force:
                return self.send_json({"current": VERSION, "update": False,
                                       "disabled": True})
            return self.send_json(updater.check(force=force))

        if path == "/api/cards.pdf":
            c = query.get("count", [None])[0]
            c = int(c) if (c and c.isdigit()) else None
            class_name = query.get("class", [None])[0]
            if class_name:
                roster_data = load_roster()
                if class_name not in roster_data.get("classes", []):
                    return self.send_error(400, "指定班级不存在")
            try:
                pdf = build_cards_pdf(count=c, class_name=class_name, paper=query.get("paper", ["a4"])[0])
            except Exception as e:
                return self.send_error(500, f"Błąd generowania kart: {e}")
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition",
                             'attachment; filename="karty_QuizScanner.pdf"')
            self.send_header("Content-Length", str(len(pdf)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(pdf)
            return

        # API
        if path == "/api/native/sync":
            global _native_seen
            now = time.monotonic()
            if now - _native_seen > 6 and session.input_source != "native":
                session.input_source = "native"
                session._changed()
            _native_seen = now
            after = query.get("after", [""])[0]
            if after == str(session.revision):
                _state_changed.wait(1.0)
                _state_changed.clear()
            return self.send_json(session.state(full=True, include_students=True))
        if path == "/api/sessions":
            directory = os.path.join(DATA_DIR, "sessions")
            items = []
            if os.path.isdir(directory):
                for name in sorted(os.listdir(directory), key=lambda item: os.path.getmtime(os.path.join(directory, item)), reverse=True):
                    try:
                        with open(os.path.join(directory, name), encoding="utf-8") as stream:
                            saved = json.load(stream)
                        items.append({"id": saved["session_id"], "title": saved["quiz"]["title"],
                                      "class_name": saved["active_class"], "phase": saved["phase"]})
                    except (ValueError, OSError, KeyError):
                        continue
            return self.send_json({"sessions": items})
        if path == "/api/state":
            full = query.get("full", ["0"])[0] == "1"
            include_students = query.get("live", ["0"])[0] == "1"
            st = session.state(full=full, include_students=include_students)
            st["countdown_enabled"] = bool(settings.get("countdown_enabled", True))
            st["scan_visibility"] = settings.get("scan_visibility", "status")
            st["show_student_answers_on_reveal"] = bool(
                settings.get("show_student_answers_on_reveal", True)
            )
            st["native_connected"] = time.monotonic() - _native_seen < 6
            if full:
                st["camera_ok"] = bool(scanner and scanner.camera_ok)
            return self.send_json(st)
        if path == "/api/quizzes":
            active = session.quiz_name
            quizzes = list_quizzes()
            details = []
            for name in quizzes:
                try:
                    quiz = read_quiz(name)
                    count = len(quiz.get("questions", []))
                except Exception:
                    count = 0
                details.append({"name": name, "question_count": count})
            return self.send_json({"quizzes": quizzes, "active": active,
                                   "details": details})
        if path == "/api/quiz":
            name = query.get("name", [""])[0]
            try:
                return self.send_json(read_quiz(name))
            except FileNotFoundError:
                return self.send_error(404, "Brak quizu")
        if path == "/api/roster":
            return self.send_json(load_roster())
        if path == "/api/settings":
            return self.send_json(settings)
        if path.startswith("/media/"):
            fn = os.path.basename(path[len("/media/"):])
            return self.send_file(os.path.join(MEDIA_DIR, fn))
        if path == "/api/quiz/export":
            name = query.get("name", [""])[0]
            try:
                quiz = read_quiz(name)
            except FileNotFoundError:
                return self.send_error(404, "Brak quizu")
            body = export_quiz_bundle(quiz).encode("utf-8")
            fname = safe_name(name) + ".quiz"
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition",
                             f'attachment; filename="{fname}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/meta":
            addresses = lan_ips()
            return self.send_json({
                "lan_ip": addresses[0] if addresses else "127.0.0.1",
                "lan_ips": addresses,
                "hotspot_ip": next((address for address in addresses
                                    if address.startswith("192.168.137.")), None),
                "port": self.server.server_address[1],
                "camera_ok": bool(scanner and scanner.camera_ok),
                "version": VERSION,
                "native_protocol": 1,
                "pair_code": _pair_code if self.authorized() else None,
                "report_dir": REPORT_DIR,
                "data_dir": DATA_DIR,
            })

        return self.send_error(404, "Nie znaleziono")

    # ---- POST ----
    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/api/native/pair":
            data = self.read_json_body()
            peer = self.client_address[0]
            now = time.monotonic()
            hits = [stamp for stamp in _pair_attempts.get(peer, []) if now - stamp < 60]
            if len(hits) >= 10:
                return self.send_json({"ok": False, "error": "配对尝试过多，请稍后再试。"}, code=429)
            _pair_attempts[peer] = hits + [now]
            if not secrets.compare_digest(str(data.get("code", "")), _pair_code):
                return self.send_json({"ok": False, "error": "配对码已失效，请重新扫描电脑上的二维码。"}, code=403)
            return self.send_json({"ok": True, "token": _pair_token})
        if path.startswith("/api/") and not self.authorized():
            return self.send_json({"ok": False, "error": "请先扫码配对"}, code=401)
        if path == "/api/camera/frame":
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                length = 0
            if length <= 0:
                return self.send_json({"ok": False, "error": "没有收到手机摄像头图像。"}, code=400)
            if length > 3 * 1024 * 1024:
                return self.send_json({"ok": False, "error": "摄像头图像超过 3 MB。"}, code=413)
            encoded = self.rfile.read(length)
            if len(encoded) != length:
                return self.send_json({"ok": False, "error": "摄像头图像传输不完整。"}, code=400)
            active_scanner = scanner
            if not active_scanner or not active_scanner.accepts_phone_frames():
                return self.send_json({"ok": False, "error": "请先在手机教师端开启本机摄像头。"}, code=409)
            try:
                image_rotation = int(self.headers.get("X-Image-Rotation", "0")) % 360
            except ValueError:
                image_rotation = 0
            try:
                display_rotation = int(self.headers.get("X-Display-Rotation", "0")) % 360
            except ValueError:
                display_rotation = 0
            if image_rotation not in (0, 90, 180, 270):
                image_rotation = 0
            if display_rotation not in (0, 90, 180, 270):
                display_rotation = 0
            if not active_scanner.submit_phone_jpeg(
                    encoded, image_rotation=image_rotation,
                    display_rotation=display_rotation):
                return self.send_json({"ok": False, "error": "无法解码手机摄像头图像。"}, code=400)
            return self.send_json({"ok": True})
        if path == "/api/quiz/import-docx":
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                length = 0
            if length > 12 * 1024 * 1024:
                return self.send_error(413, "DOCX 文件请求超过 12 MB")
        if path == "/api/roster/import":
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                length = 0
            if length > 5 * 1024 * 1024:
                return self.send_error(413, "Plik listy uczniów jest za duży")
        data = self.read_json_body()
        if path in ("/api/roster", "/api/roster/class", "/api/roster/class/create") and session.phase == "question":
            return self.send_json({"ok": False, "error": "请先结束作答，再修改或切换班级名单。"}, code=409)

        if path == "/api/native/import":
            try:
                sid = str(data.get("id", ""))
                if not re.fullmatch(r"[a-f0-9]{32}", sid):
                    raise ValueError("离线课堂编号无效")
                destination = os.path.join(DATA_DIR, "sessions", sid + ".json")
                if os.path.exists(destination):
                    return self.send_json({"ok": True, "already_imported": True})
                quiz = read_quiz(data.get("quiz_name", ""))
                if quiz != data.get("quiz"):
                    raise ValueError("电脑测验已修改，请保留手机记录并核对题目后再导入。")
                current_roster = load_roster()
                if data.get("class_name") not in current_roster.get("classes", []):
                    raise ValueError("电脑端未找到对应班级")
                def mapping(records):
                    return sorted((str(item.get("student_no")), str(item.get("name")), int(item.get("card_id"))) for item in records)
                expected_roster = [item for item in current_roster["students"] if item["class_name"] == data["class_name"]]
                if mapping(expected_roster) != mapping(data.get("roster", [])):
                    raise ValueError("该班名单或卡片映射已改变，请保留手机记录并核对后再导入。")
                imported = QuizSession()
                imported.set_roster(current_roster)
                imported.set_active_class(data["class_name"])
                imported.load_quiz(quiz, safe_name(data["quiz_name"]))
                imported.session_id = sid
                for item in data.get("history", []):
                    index = int(item["index"])
                    if not 0 <= index < len(quiz["questions"]):
                        raise ValueError("离线记录题号超出范围")
                    imported.goto(index)
                    imported.start_question(countdown_enabled=False)
                    imported.record_answers(item.get("answers", {}))
                    imported.end_question()
                write_json(destination, imported.snapshot())
                paths = report_mod.save(report_mod.build(imported), REPORT_DIR)
                return self.send_json({"ok": True, "paths": paths})
            except (ValueError, KeyError, TypeError, OSError) as error:
                return self.send_json({"ok": False, "error": str(error)}, code=400)
        if path == "/api/native/answers":
            with session.lock:
                if (data.get("session_id") != session.session_id or
                        data.get("attempt_id") != session.attempt_id or
                        data.get("class_name") != session.active_class):
                    return self.send_json({"ok": False, "error": "作答已过期，请同步当前题目。"}, code=409)
                accepted = session.record_answers(data.get("answers", {}),
                                                  attempt_id=data.get("attempt_id"),
                                                  event_id=data.get("event_id"))
            return self.send_json({"ok": bool(accepted)})
        if path == "/api/sessions/resume":
            sid = str(data.get("id", ""))
            if not re.fullmatch(r"[a-f0-9]{32}", sid):
                return self.send_json({"ok": False, "error": "课堂编号无效"}, code=400)
            try:
                with open(os.path.join(DATA_DIR, "sessions", sid + ".json"), encoding="utf-8") as stream:
                    saved = json.load(stream)
                checkpoint(session)
                session.restore(saved)
                return self.send_json({"ok": True})
            except (OSError, ValueError):
                return self.send_json({"ok": False, "error": "课堂记录无法恢复"}, code=400)
        if path == "/api/control":
            try:
                with session.lock:
                    command_id = data.get("command_id")
                    if command_id and command_id in _command_ids:
                        return self.send_json({"ok": True, "state": session.state(full=True, include_students=True)})
                    if data.get("expected_attempt") and data["expected_attempt"] != session.attempt_id:
                        return self.send_json({"ok": False, "error": "题目状态已改变，请重试。"}, code=409)
                    result = self.control_action(data)
                    if command_id:
                        _command_ids[command_id] = True
                        if len(_command_ids) > 2000:
                            _command_ids.pop(next(iter(_command_ids)))
                    session._changed()
                    return result
            except (ValueError, TypeError) as error:
                return self.send_json({"ok": False, "error": str(error)}, code=400)


        if path == "/api/quiz":
            name = safe_name(data.get("name", ""))
            quiz = data.get("quiz", {})
            write_quiz(name, quiz)
            return self.send_json({"ok": True, "name": name})

        if path == "/api/quiz/delete":
            delete_quiz(data.get("name", ""))
            return self.send_json({"ok": True})

        if path == "/api/load":
            name = data.get("name", "")
            try:
                quiz = read_quiz(name)
            except FileNotFoundError:
                return self.send_error(404, "Brak quizu")
            session.load_quiz(quiz, safe_name(name))
            return self.send_json({"ok": True, "state": session.state(full=True)})

        if path == "/api/roster":
            try:
                roster = save_roster(data)
            except ValueError as e:
                return self.send_json({"ok": False, "error": str(e)}, code=400)
            session.set_roster(roster)
            return self.send_json({"ok": True, "roster": roster})

        if path == "/api/roster/class/create":
            class_name = str(data.get("class_name") or "").strip()
            if not class_name:
                return self.send_json({"ok": False, "error": "请输入班级名称。"}, code=400)
            if len(class_name) > 60:
                return self.send_json({"ok": False, "error": "班级名称不能超过 60 个字符。"}, code=400)
            roster = load_roster()
            if class_name in roster.get("classes", []):
                return self.send_json({"ok": False, "error": "该班级已存在。"}, code=409)
            roster["classes"] = [*roster.get("classes", []), class_name]
            roster["active_class"] = class_name
            roster = save_roster(roster)
            session.set_roster(roster)
            return self.send_json({"ok": True, "roster": roster})

        if path == "/api/roster/class":
            class_name = str(data.get("class_name") or "").strip()
            roster = load_roster()
            if class_name not in roster.get("classes", []):
                return self.send_json({"ok": False, "error": "请选择名单中的班级。"}, code=400)
            roster["active_class"] = class_name
            roster = save_roster(roster)
            session.set_roster(roster)
            return self.send_json({"ok": True, "active_class": class_name})

        if path == "/api/roster/import":
            try:
                roster = parse_roster_upload(
                    data.get("filename"), data.get("content_base64"),
                    default_class_name=data.get("class_name"),
                )
            except ValueError as e:
                return self.send_json({"ok": False, "error": str(e)}, code=400)
            return self.send_json({"ok": True,
                                   "count": len(roster.get("students", [])),
                                   "classes": roster.get("classes", []),
                                   "roster": roster})

        if path == "/api/export":
            fmts = data.get("formats") or list(AUTOSAVE_FORMATS)
            fmts = [f for f in fmts if f in report_mod.RENDERERS]
            query = {key: [data[key]] for key in ("class", "session") if data.get(key)}
            paths = report_mod.save(report_mod.build(report_session(query), class_name=data.get("class")), REPORT_DIR, fmts or AUTOSAVE_FORMATS)
            return self.send_json({"ok": bool(paths), "paths": paths,
                                   "dir": REPORT_DIR})

        if path == "/api/update/apply":
            res = updater.apply()
            if res.get("script"):
                global pending_swap
                pending_swap = res["script"]
            return self.send_json(res)

        if path == "/api/settings":
            if "camera" in data:
                session.input_source = "camera"
            changed_cam = ("camera" in data and
                           str(data["camera"]) != str(settings.get("camera")))
            for k in DEFAULT_SETTINGS:
                if k in data:
                    settings[k] = data[k]
            settings["countdown_enabled"] = bool(settings.get("countdown_enabled", True))
            settings["scan_visibility"] = (
                "status" if settings.get("scan_visibility") == "status" else "answer"
            )
            settings["show_student_answers_on_reveal"] = bool(
                settings.get("show_student_answers_on_reveal", True)
            )
            settings["sound"] = False
            if not settings["countdown_enabled"]:
                session.set_auto_mode(False)
            save_settings()
            apply_settings()
            session._changed()
            if changed_cam:
                restart_camera()
            return self.send_json({"ok": True, "settings": settings})

        if path == "/api/media":
            try:
                fname, kind = save_media(data.get("data", ""), data.get("name", ""))
            except ValueError as e:
                return self.send_json({"ok": False, "error": str(e)}, code=400)
            return self.send_json({"ok": True, "file": fname, "type": kind})

        if path == "/api/quiz/import":
            bundle = data.get("quiz")
            name = safe_name(data.get("name", "") or (bundle or {}).get("title", ""))
            if not isinstance(bundle, dict) or "questions" not in bundle:
                return self.send_json({"ok": False}, code=400)
            quiz = import_quiz_bundle(bundle)
            write_quiz(name, quiz)
            return self.send_json({"ok": True, "name": name})

        if path == "/api/quiz/import-docx":
            try:
                result = parse_docx_quiz_upload(
                    data.get("filename"), data.get("content_base64"))
            except ValueError as e:
                return self.send_json({"ok": False, "error": str(e)}, code=400)
            return self.send_json({"ok": True, **result})

        return self.send_error(404, "Nie znaleziono")

    def control_action(self, data):
        action = data.get("action")
        if action not in ("start", "end", "reveal", "next_start", "prev_start", "next", "prev", "goto", "reset", "speed_bonus", "auto_mode", "scan_visibility"):
            raise ValueError("未知课堂操作")
        if action in ("start", "next_start", "prev_start") and data.get("input_source") == "native":
            session.input_source = "native"
        if action == "start":
            countdown_enabled = data.get(
                "countdown_enabled", settings.get("countdown_enabled", True)
            )
            session.start_question(countdown_enabled=bool(countdown_enabled))
        elif action == "end":
            session.end_question()
        elif action == "reveal":
            session.reveal()
        elif action in ("next_start", "prev_start"):
            session.move_and_start("prev" if action == "prev_start" else "next")
        elif action == "next":
            session.next_question()
        elif action == "prev":
            session.prev_question()
        elif action == "goto":
            session.goto(int(data.get("index", 0)))
        elif action == "reset":
            session.reset_scores()
        elif action == "speed_bonus":
            session.set_speed_bonus(data.get("value", False))
        elif action == "auto_mode":
            enabled = bool(data.get("value", False)) and bool(
                settings.get("countdown_enabled", True)
            )
            session.set_auto_mode(enabled)
            if enabled and session.phase == PHASE_IDLE:
                session.start_question(countdown_enabled=True)
        elif action == "scan_visibility":
            value = "status" if data.get("value") == "status" else "answer"
            settings["scan_visibility"] = value
            session.set_scan_visibility(value)
            save_settings()
        state = session.state(full=True, include_students=True)
        state["countdown_enabled"] = bool(settings.get("countdown_enabled", True))
        state["scan_visibility"] = settings.get("scan_visibility", "status")
        return self.send_json({"ok": True, "state": state})


def apply_settings():
    """Przenosi ustawienia do działających obiektów (sesja, skaner)."""
    session.set_only_known(bool(settings.get("only_known", True)))
    session.set_countdown_enabled(bool(settings.get("countdown_enabled", True)))
    session.set_scan_visibility(settings.get("scan_visibility", "status"))
    session.set_show_student_answers_on_reveal(
        bool(settings.get("show_student_answers_on_reveal", True))
    )
    if scanner:
        scanner.mirror = bool(settings.get("mirror", True))
        scanner.only_known = bool(settings.get("only_known", True))


def restart_camera():
    """Zatrzymuje obecny wątek kamery i uruchamia nowy z aktualnym źródłem."""
    global scanner
    if scanner:
        scanner.stop()
        scanner = None
    camera_source = settings.get("camera", "0")
    scanner = CameraScanner(session, camera=camera_source,
                            stable_frames=3 if str(camera_source).strip().casefold() == "android" else 5,
                            mirror=bool(settings.get("mirror", True)),
                            only_known=bool(settings.get("only_known", True)))
    scanner.start()


def build_server(camera=None, port=8000, host="0.0.0.0", no_camera=False):
    """Przygotowuje sesje, wątek kamery i serwer HTTP. Zwraca obiekt httpd
    (jeszcze nie wystartowany). Używane zarówno przez CLI (main), jak i przez
    launcher uruchamiający serwer w tym samym procesie (działa w .exe)."""
    global scanner

    seed_data()
    load_settings()
    apply_settings()
    if camera is not None:          # jawny wybór z linii poleceń ma pierwszeństwo
        settings["camera"] = str(camera)
    session.set_roster(load_roster())
    session.set_only_known(bool(settings.get("only_known", True)))
    session.on_podium = autosave_report
    session.start_auto_engine()
    updater.check_async(bool(settings.get("check_updates", True)))

    quizzes = list_quizzes()
    if quizzes:
        try:
            session.load_quiz(read_quiz(quizzes[0]), quizzes[0])
        except Exception:
            pass

    recovery = os.path.join(DATA_DIR, "classroom.json")
    if os.path.exists(recovery):
        try:
            with open(recovery, encoding="utf-8") as stream:
                session.restore(json.load(stream))
        except (OSError, ValueError, KeyError, TypeError):
            pass
    session.on_change = checkpoint
    if not no_camera:
        camera_source = settings.get("camera", "0")
        scanner = CameraScanner(session, camera=camera_source,
                                stable_frames=3 if str(camera_source).strip().casefold() == "android" else 5,
                                mirror=bool(settings.get("mirror", True)),
                                only_known=bool(settings.get("only_known", True)))
        scanner.start()

    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    return httpd


def stop_server(httpd):
    """Zatrzymuje serwer, wątek kamery i silnik trybu automatycznego."""
    global scanner
    if scanner:
        scanner.stop()
        scanner = None
    session.stop_auto_engine()
    if httpd:
        httpd.shutdown()
    # Pobrana aktualizacja czeka na wymianę pliku -- teraz program już nie działa.
    if pending_swap:
        updater.run_swap_script(pending_swap)


def _utf8_console():
    """Konsola Windows bywa ustawiona na stronę kodową bez polskich znaków.
    Przełączamy strumienie na UTF-8, żeby komunikaty nie wywracały programu."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main():
    _utf8_console()
    ap = argparse.ArgumentParser(description="QuizScanner 教师端服务")
    ap.add_argument("--camera", default=None,
                    help="摄像头编号（0、1…）或手机视频流地址，"
                         "例如 http://192.168.1.50:8080/video")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--no-camera", action="store_true",
                    help="不启动摄像头（例如只编辑题目时使用）。")
    args = ap.parse_args()

    httpd = build_server(camera=args.camera, port=args.port,
                         host=args.host, no_camera=args.no_camera)

    ip = lan_ip()
    if sys.stdout:  # w trybie bezokienkowym (.exe) stdout może być None
        print("=" * 58)
        print(f"  QuizScanner {VERSION} 已启动")
        print(f"  教师面板： http://localhost:{args.port}/teacher")
        print(f"  投影大屏： http://localhost:{args.port}/board")
        print(f"  题目编辑器：http://localhost:{args.port}/editor")
        print(f"  局域网投影：http://{ip}:{args.port}/board")
        print("=" * 58)
        print("  停止服务：按 Ctrl+C")

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(
            f"http://localhost:{args.port}/teacher")).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n正在停止服务…")
    finally:
        stop_server(httpd)


if __name__ == "__main__":
    main()
