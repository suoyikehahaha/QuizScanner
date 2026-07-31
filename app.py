"""
Serwer aplikacji QuizScanner (biblioteka standardowa Pythona, bez Flask).

Uruchamia:
  - watek kamery (skaner ArUco),
  - serwer HTTP z panelem nauczyciela, tablica i edytorem.

Uzycie:
  python app.py                 # kamera 0, port 8000, otwiera przegladarke
  python app.py --camera 1 --port 8000 --no-browser

Adresy:
  Panel nauczyciela : http://localhost:PORT/teacher
  Tablica (rzutnik) : http://localhost:PORT/board
  Edytor pytan      : http://localhost:PORT/editor
  Tablica w sieci   : http://<IP-w-LAN>:PORT/board
"""

import argparse
import json
import os
import re
import shutil
import socket
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from quiz_session import QuizSession
from camera_worker import CameraScanner

# Sciezki dzialaja tak samo z kodu zrodlowego, jak i w spakowanym .exe
# (PyInstaller). RES_DIR = zasoby tylko-do-odczytu (web/), DATA_DIR =
# folder zapisywalny obok programu (quizy, roster, wyniki).
if getattr(sys, "frozen", False):
    RES_DIR = sys._MEIPASS                       # rozpakowane zasoby exe
    DATA_DIR = os.path.dirname(sys.executable)   # folder z plikiem .exe
else:
    RES_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = RES_DIR

WEB_DIR = os.path.join(RES_DIR, "web")
QUIZ_DIR = os.path.join(DATA_DIR, "quizzes")
ROSTER_JSON = os.path.join(DATA_DIR, "roster.json")
STUDENTS_CSV = os.path.join(DATA_DIR, "students.csv")


def _seed_data():
    """Przy pierwszym uruchomieniu .exe kopiuje domyslne dane (quizy,
    lista uczniow) do zapisywalnego folderu obok programu."""
    if not getattr(sys, "frozen", False):
        return
    try:
        if not os.path.isdir(QUIZ_DIR):
            src = os.path.join(RES_DIR, "quizzes")
            if os.path.isdir(src):
                shutil.copytree(src, QUIZ_DIR)
        if not os.path.exists(STUDENTS_CSV):
            src = os.path.join(RES_DIR, "students.csv")
            if os.path.exists(src):
                shutil.copy(src, STUDENTS_CSV)
    except Exception:
        pass


session = QuizSession()
scanner = None  # ustawiany przy starcie serwera

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


# --------------------------- pomocnicze ---------------------------
def safe_name(name):
    """Sanityzuje nazwe pliku quizu (bez sciezek)."""
    return re.sub(r"[^A-Za-z0-9_\- ]", "", (name or "")).strip() or "quiz"


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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(quiz, f, ensure_ascii=False, indent=2)


def delete_quiz(name):
    path = os.path.join(QUIZ_DIR, safe_name(name) + ".json")
    if os.path.exists(path):
        os.remove(path)


def load_roster():
    """Roster z roster.json, a jesli brak -- ze students.csv."""
    if os.path.exists(ROSTER_JSON):
        with open(ROSTER_JSON, encoding="utf-8") as f:
            data = json.load(f)
        return {int(k): v for k, v in data.items()}
    roster = {}
    if os.path.exists(STUDENTS_CSV):
        import csv
        with open(STUDENTS_CSV, newline="", encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) >= 2 and row[0].strip().isdigit():
                    roster[int(row[0])] = row[1].strip()
    return roster


def save_roster(roster):
    with open(ROSTER_JSON, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in roster.items()}, f, ensure_ascii=False, indent=2)


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


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def build_cards_pdf(count=None):
    """Tworzy w pamieci PDF z kartami ArUco (jedna karta na strone A4).
    Domyslnie karty dla aktualnej listy uczniow; jesli lista pusta lub podano
    count -- karty o numerach 0..count-1."""
    import io
    import cv2
    from PIL import Image
    from aruco_common import get_dictionary
    from generate_cards import make_card

    dictionary = get_dictionary()
    with session.lock:
        roster = dict(session.roster)

    if roster and not count:
        ids = sorted(roster)
    else:
        ids = list(range(count or 30))

    W, H = 1165, 1653              # ~A5 przy 200 DPI
    marker_px = int(min(W, H) * 0.55)
    pages = []
    for mid in ids:
        card = make_card(mid, roster.get(mid, ""), dictionary, (W, H), marker_px)
        pages.append(Image.fromarray(cv2.cvtColor(card, cv2.COLOR_BGR2RGB)))

    buf = io.BytesIO()
    if pages:
        pages[0].save(buf, format="PDF", save_all=True,
                      append_images=pages[1:], resolution=200.0)
    return buf.getvalue()


def export_results():
    import csv
    import datetime as dt
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(DATA_DIR, f"wyniki_{stamp}.csv")
    with session.lock:
        board = session.leaderboard()
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["miejsce", "id", "imie", "punkty"])
        for i, row in enumerate(board, 1):
            wr.writerow([i, row["id"], row["name"], row["score"]])
    return path


# --------------------------- handler ---------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "QuizScanner/1.0"

    def log_message(self, *args):
        pass  # cisza w konsoli

    # ---- odpowiedzi ----
    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
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
            # Tryb bez kamery -- pojedynczy statyczny kadr zastepczy.
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
        self.end_headers()
        try:
            while True:
                jpg = scanner.get_jpeg() if scanner else None
                if jpg:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(("Content-Length: %d\r\n\r\n" % len(jpg)).encode())
                    self.wfile.write(jpg)
                    self.wfile.write(b"\r\n")
                time.sleep(0.04)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    # ---- GET ----
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            return self.redirect("/teacher")
        if path == "/teacher":
            return self.send_file(os.path.join(WEB_DIR, "teacher.html"))
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

        if path == "/api/cards.pdf":
            c = query.get("count", [None])[0]
            c = int(c) if (c and c.isdigit()) else None
            try:
                pdf = build_cards_pdf(count=c)
            except Exception as e:
                return self.send_error(500, f"Blad generowania kart: {e}")
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
        if path == "/api/state":
            full = query.get("full", ["0"])[0] == "1"
            st = session.state(full=full)
            if full:
                st["camera_ok"] = bool(scanner and scanner.camera_ok)
            return self.send_json(st)
        if path == "/api/quizzes":
            active = session.quiz_name
            return self.send_json({"quizzes": list_quizzes(), "active": active})
        if path == "/api/quiz":
            name = query.get("name", [""])[0]
            try:
                return self.send_json(read_quiz(name))
            except FileNotFoundError:
                return self.send_error(404, "Brak quizu")
        if path == "/api/roster":
            return self.send_json(load_roster())
        if path == "/api/meta":
            return self.send_json({
                "lan_ip": lan_ip(),
                "port": self.server.server_address[1],
                "camera_ok": bool(scanner and scanner.camera_ok),
            })

        return self.send_error(404, "Nie znaleziono")

    # ---- POST ----
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        data = self.read_json_body()

        if path == "/api/control":
            action = data.get("action")
            if action == "start":
                session.start_question()
            elif action == "reveal":
                session.reveal()
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
            return self.send_json({"ok": True, "state": session.state(full=True)})

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
            roster = {int(k): v for k, v in data.items()}
            save_roster(roster)
            session.set_roster(roster)
            return self.send_json({"ok": True})

        if path == "/api/export":
            p = export_results()
            return self.send_json({"ok": True, "path": p})

        return self.send_error(404, "Nie znaleziono")


def build_server(camera=0, port=8000, host="0.0.0.0", no_camera=False):
    """Przygotowuje sesje, watek kamery i serwer HTTP. Zwraca obiekt httpd
    (jeszcze nie wystartowany). Uzywane zarowno przez CLI (main), jak i przez
    launcher uruchamiajacy serwer w tym samym procesie (dziala w .exe)."""
    global scanner

    _seed_data()
    session.set_roster(load_roster())

    quizzes = list_quizzes()
    if quizzes:
        try:
            session.load_quiz(read_quiz(quizzes[0]), quizzes[0])
        except Exception:
            pass

    if not no_camera:
        scanner = CameraScanner(session, camera=camera)
        scanner.start()

    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    return httpd


def stop_server(httpd):
    """Zatrzymuje serwer i watek kamery."""
    global scanner
    if scanner:
        scanner.stop()
        scanner = None
    if httpd:
        httpd.shutdown()


def main():
    ap = argparse.ArgumentParser(description="Serwer QuizScanner")
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--no-camera", action="store_true",
                    help="Uruchom bez kamery (np. do edycji quizow).")
    args = ap.parse_args()

    httpd = build_server(camera=args.camera, port=args.port,
                         host=args.host, no_camera=args.no_camera)

    ip = lan_ip()
    if sys.stdout:  # w trybie bezokienkowym (.exe) stdout moze byc None
        print("=" * 58)
        print("  QuizScanner uruchomiony")
        print(f"  Panel nauczyciela : http://localhost:{args.port}/teacher")
        print(f"  Tablica (rzutnik) : http://localhost:{args.port}/board")
        print(f"  Edytor pytan      : http://localhost:{args.port}/editor")
        print(f"  Tablica w sieci   : http://{ip}:{args.port}/board")
        print("=" * 58)
        print("  Zatrzymanie: Ctrl+C")

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(
            f"http://localhost:{args.port}/teacher")).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nZatrzymywanie...")
    finally:
        stop_server(httpd)


if __name__ == "__main__":
    main()
