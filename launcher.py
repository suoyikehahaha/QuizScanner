"""
Launcher QuizScanner (okno z przyciskami).

Uruchamia serwer aplikacji w TYM SAMYM procesie (w watku), dzieki czemu
dziala tak samo z kodu zrodlowego (`python launcher.py`), jak i spakowany
w jeden plik `QuizScanner.exe` (PyInstaller). Daje przyciski do otwierania
panelu nauczyciela, tablicy i edytora w przegladarce.
"""

import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox

import app  # build_server / stop_server / lan_ip


class Launcher:
    def __init__(self, root):
        self.root = root
        self.httpd = None
        self.thread = None
        root.title("QuizScanner")
        root.geometry("460x330")
        root.resizable(False, False)
        root.configure(bg="#14161f")

        tk.Label(root, text="QuizScanner", font=("Segoe UI", 22, "bold"),
                 fg="#e2603f", bg="#14161f").pack(pady=(18, 2))
        tk.Label(root, text="System quizowy z odczytem kart z kamery",
                 fg="#8b91a4", bg="#14161f").pack()

        cfg = tk.Frame(root, bg="#14161f")
        cfg.pack(pady=14)
        tk.Label(cfg, text="Kamera:", fg="#eef0f6", bg="#14161f").grid(row=0, column=0, padx=6, sticky="e")
        self.cam = tk.Spinbox(cfg, from_=0, to=8, width=5)
        self.cam.grid(row=0, column=1, padx=6)
        tk.Label(cfg, text="Port:", fg="#eef0f6", bg="#14161f").grid(row=0, column=2, padx=6, sticky="e")
        self.port = tk.Entry(cfg, width=7)
        self.port.insert(0, "8000")
        self.port.grid(row=0, column=3, padx=6)

        self.startBtn = tk.Button(root, text="▶  Uruchom", bg="#4faa6a", fg="white",
                                  font=("Segoe UI", 12, "bold"), relief="flat",
                                  padx=16, pady=9, command=self.toggle, activebackground="#3f9159")
        self.startBtn.pack(pady=6)

        links = tk.Frame(root, bg="#14161f")
        links.pack(pady=8)
        self.b_teacher = self._link(links, "🎛  Panel nauczyciela", "teacher", 0)
        self.b_board = self._link(links, "📺  Tablica", "board", 1)
        self.b_editor = self._link(links, "✏️  Edytor", "editor", 2)
        self._set_links(False)

        self.status = tk.Label(root, text="Zatrzymany", fg="#8b91a4", bg="#14161f")
        self.status.pack(pady=(12, 0))

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _link(self, parent, text, path, col):
        b = tk.Button(parent, text=text, relief="flat", bg="#242938", fg="#eef0f6",
                      activebackground="#313749", activeforeground="#fff",
                      padx=10, pady=6, command=lambda: self.open(path))
        b.grid(row=0, column=col, padx=5)
        return b

    def _set_links(self, on):
        state = "normal" if on else "disabled"
        for b in (self.b_teacher, self.b_board, self.b_editor):
            b.config(state=state)

    def toggle(self):
        if self.httpd:
            self.stop()
        else:
            self.start()

    def start(self):
        port = int(self.port.get().strip() or "8000")
        cam = int(self.cam.get().strip() or "0")
        try:
            self.httpd = app.build_server(camera=cam, port=port, host="0.0.0.0")
        except OSError as e:
            messagebox.showerror("QuizScanner",
                                 f"Nie udalo sie uruchomic na porcie {port}.\n"
                                 f"Sprobuj innego portu.\n\n{e}")
            self.httpd = None
            return
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.startBtn.config(text="■  Zatrzymaj", bg="#d9573d", activebackground="#c44e30")
        self._set_links(True)
        ip = app.lan_ip()
        self.status.config(text=f"Dziala · Tablica w sieci: http://{ip}:{port}/board", fg="#4faa6a")
        self.root.after(900, lambda: self.open("teacher"))

    def stop(self):
        if self.httpd:
            app.stop_server(self.httpd)
            self.httpd = None
        self.startBtn.config(text="▶  Uruchom", bg="#4faa6a", activebackground="#3f9159")
        self._set_links(False)
        self.status.config(text="Zatrzymany", fg="#8b91a4")

    def open(self, path):
        port = self.port.get().strip() or "8000"
        webbrowser.open(f"http://localhost:{port}/{path}")

    def on_close(self):
        self.stop()
        self.root.destroy()


def run():
    root = tk.Tk()
    Launcher(root)
    root.mainloop()


def _selftest():
    """Diagnostyka: startuje serwer, odpytuje sie, zapisuje wynik do pliku."""
    import json
    import os
    import tempfile
    import threading
    import time
    import traceback
    import urllib.request
    logp = os.path.join(tempfile.gettempdir(), "qs_selftest.txt")
    try:
        httpd = app.build_server(port=8061, no_camera=True)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        time.sleep(1.0)
        st = json.load(urllib.request.urlopen("http://127.0.0.1:8061/api/state"))
        html = urllib.request.urlopen("http://127.0.0.1:8061/teacher").read()
        pdf = urllib.request.urlopen("http://127.0.0.1:8061/api/cards.pdf?count=3").read()
        pdf_ok = pdf[:4] == b"%PDF"
        msg = (f"OK quiz={st['quiz_title']} total={st['total']} "
               f"teacher_bytes={len(html)} cards_pdf_ok={pdf_ok} pdf_bytes={len(pdf)}")
        app.stop_server(httpd)
    except Exception:
        msg = "FAIL\n" + traceback.format_exc()
    with open(logp, "w", encoding="utf-8") as f:
        f.write(msg)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        sys.exit(0)
    # Tryb konsolowy (bez okna): QuizScanner.exe --serve [--port ... --no-camera]
    if "--serve" in sys.argv:
        sys.argv.remove("--serve")
        app.main()
    else:
        run()
