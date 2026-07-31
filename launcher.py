"""
Natywny launcher QuizScanner (Tkinter).

Uruchamia serwer aplikacji w osobnym procesie i daje przyciski do
otwierania panelu nauczyciela, tablicy i edytora w przegladarce.
Alternatywa dla uruchamiania 'python app.py' z konsoli.
"""

import os
import socket
import subprocess
import sys
import tkinter as tk
import webbrowser
from tkinter import ttk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class Launcher:
    def __init__(self, root):
        self.root = root
        self.proc = None
        root.title("QuizScanner")
        root.geometry("440x320")
        root.resizable(False, False)

        tk.Label(root, text="QuizScanner", font=("Segoe UI", 20, "bold"),
                 fg="#7b2ff7").pack(pady=(16, 2))
        tk.Label(root, text="System quizowy z odczytem kart z kamery",
                 fg="#666").pack()

        cfg = tk.Frame(root)
        cfg.pack(pady=14)
        tk.Label(cfg, text="Kamera:").grid(row=0, column=0, padx=6, sticky="e")
        self.cam = tk.Spinbox(cfg, from_=0, to=8, width=5)
        self.cam.grid(row=0, column=1, padx=6)
        tk.Label(cfg, text="Port:").grid(row=0, column=2, padx=6, sticky="e")
        self.port = tk.Entry(cfg, width=7)
        self.port.insert(0, "8000")
        self.port.grid(row=0, column=3, padx=6)

        self.startBtn = tk.Button(root, text="▶  Uruchom serwer", bg="#26890c",
                                  fg="white", font=("Segoe UI", 12, "bold"),
                                  relief="flat", padx=14, pady=8, command=self.toggle)
        self.startBtn.pack(pady=6)

        links = tk.Frame(root)
        links.pack(pady=8)
        self.b_teacher = self._link(links, "🎛  Panel nauczyciela", "teacher", 0)
        self.b_board = self._link(links, "📺  Tablica", "board", 1)
        self.b_editor = self._link(links, "✏️  Edytor", "editor", 2)
        self._set_links(False)

        self.status = tk.Label(root, text="Serwer zatrzymany", fg="#999")
        self.status.pack(pady=(10, 0))

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _link(self, parent, text, path, col):
        b = tk.Button(parent, text=text, relief="flat", bg="#eef0f4",
                      padx=10, pady=6, command=lambda: self.open(path))
        b.grid(row=0, column=col, padx=5)
        return b

    def _set_links(self, on):
        state = "normal" if on else "disabled"
        for b in (self.b_teacher, self.b_board, self.b_editor):
            b.config(state=state)

    def toggle(self):
        if self.proc:
            self.stop()
        else:
            self.start()

    def start(self):
        port = self.port.get().strip() or "8000"
        cam = self.cam.get().strip() or "0"
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self.proc = subprocess.Popen(
            [sys.executable, os.path.join(BASE_DIR, "app.py"),
             "--no-browser", "--camera", cam, "--port", port],
            cwd=BASE_DIR, creationflags=flags)
        self.startBtn.config(text="■  Zatrzymaj serwer", bg="#e21b3c")
        self._set_links(True)
        ip = lan_ip()
        self.status.config(
            text=f"Działa · Tablica w sieci: http://{ip}:{port}/board", fg="#26890c")
        self.root.after(1200, lambda: self.open("teacher"))

    def stop(self):
        if self.proc:
            self.proc.terminate()
            self.proc = None
        self.startBtn.config(text="▶  Uruchom serwer", bg="#26890c")
        self._set_links(False)
        self.status.config(text="Serwer zatrzymany", fg="#999")

    def open(self, path):
        port = self.port.get().strip() or "8000"
        webbrowser.open(f"http://localhost:{port}/{path}")

    def on_close(self):
        self.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    Launcher(root)
    root.mainloop()
