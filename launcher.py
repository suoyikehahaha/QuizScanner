"""
Launcher QuizScanner (okno z przyciskami).

Uruchamia serwer aplikacji w TYM SAMYM procesie (w wątku), dzięki czemu
działa tak samo z kodu źródłowego (`python launcher.py`), jak i spakowany
w jeden plik `QuizScanner.exe` (PyInstaller). Daje przyciski do otwierania
panelu nauczyciela, tablicy i edytora w przeglądarce.
"""

import sys
import json
import os
import threading
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from tkinter import messagebox

from quizscanner import server as app  # build_server / stop_server / lan_ip
from quizscanner import VERSION
from quizscanner.paths import ICON_ICO


class Launcher:
    def __init__(self, root):
        self.root = root
        self.httpd = None
        self.thread = None
        self.external_server = False
        self.external_port = None
        root.title("QuizScanner")
        try:                                   # logo w pasku okna i na pasku zadań
            root.iconbitmap(ICON_ICO)
        except Exception:                      # brak pliku lub system bez .ico
            pass
        root.geometry("500x426")
        root.resizable(False, False)
        root.configure(bg="#14161f")

        tk.Label(root, text="QuizScanner", font=("Segoe UI", 22, "bold"),
                 fg="#e2603f", bg="#14161f").pack(pady=(18, 2))
        tk.Label(root, text=f"课堂测验与答题卡实时识别  ·  v{VERSION}",
                 fg="#8b91a4", bg="#14161f").pack()

        cfg = tk.Frame(root, bg="#14161f")
        cfg.pack(pady=14)
        tk.Label(cfg, text="摄像头：", fg="#eef0f6", bg="#14161f").grid(row=0, column=0, padx=6, sticky="e")
        self.cam = tk.Spinbox(cfg, from_=0, to=8, width=5)
        self.cam.grid(row=0, column=1, padx=6)
        tk.Label(cfg, text="端口：", fg="#eef0f6", bg="#14161f").grid(row=0, column=2, padx=6, sticky="e")
        self.port = tk.Entry(cfg, width=7)
        # Avoid colliding with other local development servers on port 8000.
        self.port.insert(0, "8012")
        self.port.grid(row=0, column=3, padx=6)

        self.startBtn = tk.Button(root, text="▶  启动服务", bg="#4faa6a", fg="white",
                                  font=("Segoe UI", 12, "bold"), relief="flat",
                                  padx=16, pady=9, command=self.toggle, activebackground="#3f9159")
        self.startBtn.pack(pady=6)

        self.hotspotBtn = tk.Button(root, text="📶  打开电脑移动热点设置",
                                    bg="#242938", fg="#eef0f6", relief="flat",
                                    padx=12, pady=5, command=self.open_hotspot_settings)
        self.hotspotBtn.pack(pady=(0, 5))
        self.connectionHelpBtn = tk.Button(
            root, text="📱  电脑不能开热点？查看连接方法",
            bg="#242938", fg="#eef0f6", relief="flat",
            padx=12, pady=5, command=self.show_connection_help,
        )
        self.connectionHelpBtn.pack(pady=(0, 5))

        links = tk.Frame(root, bg="#14161f")
        links.pack(pady=8)
        self.b_teacher = self._link(links, "🎛  教师面板", "teacher", 0)
        self.b_board = self._link(links, "📺  投影大屏", "board", 1)
        self.b_editor = self._link(links, "✏️  题目编辑器", "editor", 2)
        self._set_links(False)

        self.status = tk.Label(root, text="服务未启动", fg="#8b91a4", bg="#14161f")
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
        if self.external_server:
            self.open("teacher")
        elif self.httpd:
            self.stop()
        else:
            self.start()

    def _existing_server(self, port):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/meta", timeout=0.7) as response:
                meta = json.load(response)
            if meta.get("port") == port and meta.get("version"):
                return meta
        except (OSError, ValueError, urllib.error.URLError):
            pass
        return None

    def _set_running_status(self, port, meta=None):
        meta = meta or {}
        addresses = meta.get("lan_ips") or app.lan_ips()
        hotspot_ip = meta.get("hotspot_ip") or next(
            (address for address in addresses if address.startswith("192.168.137.")), None
        )
        address = hotspot_ip or meta.get("lan_ip") or (addresses[0] if addresses else "127.0.0.1")
        if hotspot_ip:
            text = f"服务运行中 · 手机电脑热点地址：http://{address}:{port}/mobile"
        elif addresses:
            text = f"服务运行中 · 手机可连同一 Wi-Fi：http://{address}:{port}/mobile"
        else:
            text = "服务运行中 · 未发现局域网地址，请连接路由器、检查网络或查看手机连接帮助"
        self.status.config(text=text, fg="#4faa6a")
        if not hotspot_ip and not addresses and sys.platform == "win32":
            self.root.after(1200, self.open_hotspot_settings)

    def open_hotspot_settings(self):
        if sys.platform != "win32":
            messagebox.showinfo("QuizScanner", "请在 Windows 网络设置中打开移动热点。")
            return
        try:
            os.startfile("ms-settings:network-mobilehotspot")
        except OSError as e:
            messagebox.showerror("QuizScanner", f"无法打开移动热点设置。\n\n{e}")

    def show_connection_help(self):
        port = self.external_port or self.port.get().strip() or "8012"
        addresses = app.lan_ips()
        urls = "\n".join(f"http://{address}:{port}/mobile" for address in addresses[:6])
        if not urls:
            urls = f"启动服务并让电脑连接网络后，此处会显示地址。端口：{port}"
        messagebox.showinfo(
            "手机连接 QuizScanner",
            "电脑不能开启移动热点时，不影响使用。\n\n"
            "1. 让电脑和手机连接同一台路由器的 Wi-Fi；电脑也可以用网线连接该路由器。\n"
            "2. 在手机 APK 的电脑地址栏填写下面任意一个地址：\n"
            f"{urls}\n\n"
            "请避开禁止设备互访的访客网络，并允许 QuizScanner 通过 Windows 专用网络防火墙。\n"
            "如果两台设备之间没有任何共同网络，需要先提供路由器或可用的无线接入点。",
        )

    def start(self):
        port = int(self.port.get().strip() or "8000")
        existing = self._existing_server(port)
        if existing:
            if existing.get("version") != VERSION:
                running_version = existing.get("version") or "未知"
                self.status.config(
                    text=f"端口 {port} 正在运行 QuizScanner {running_version}，请关闭旧版或更换端口",
                    fg="#d7a64a",
                )
                messagebox.showwarning(
                    "检测到其他版本",
                    f"端口 {port} 上正在运行 QuizScanner {running_version}。\n"
                    "请先关闭旧版，或将端口改为其他未占用的端口后再启动。",
                )
                return
            self.external_server = True
            self.external_port = port
            self.port.config(state="disabled")
            self.startBtn.config(text="打开教师面板", bg="#3659ad", activebackground="#2d4c96")
            self._set_links(True)
            self._set_running_status(port, existing)
            self.root.after(900, lambda: self.open("teacher"))
            return

        self.external_server = False
        self.external_port = None
        self.port.config(state="normal")
        cam = int(self.cam.get().strip() or "0")
        try:
            self.httpd = app.build_server(camera=cam, port=port, host="0.0.0.0")
        except OSError as e:
            messagebox.showerror("QuizScanner",
                                 f"无法在端口 {port} 启动服务。\n"
                                 f"请尝试其他端口。\n\n{e}")
            self.httpd = None
            return
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.startBtn.config(text="■  停止服务", bg="#d9573d", activebackground="#c44e30")
        self._set_links(True)
        self._set_running_status(port)
        self.root.after(900, lambda: self.open("teacher"))

    def stop(self):
        if self.httpd:
            app.stop_server(self.httpd)
            self.httpd = None
        self.startBtn.config(text="▶  启动服务", bg="#4faa6a", activebackground="#3f9159")
        self.startBtn.config(command=self.toggle)
        self.port.config(state="normal")
        self.external_server = False
        self.external_port = None
        self._set_links(False)
        self.status.config(text="服务未启动", fg="#8b91a4")

    def open(self, path):
        port = self.external_port or self.port.get().strip() or "8000"
        webbrowser.open(f"http://localhost:{port}/{path}")

    def on_close(self):
        self.stop()
        self.root.destroy()


def run():
    root = tk.Tk()
    launcher = Launcher(root)
    root.after(350, launcher.start)
    root.mainloop()


if __name__ == "__main__":
    # Diagnostyka przeniesiona do tools/selftest.py (działa bez tkintera).
    # Tryb konsolowy (bez okna): QuizScanner.exe --serve [--port ... --no-camera]
    if "--serve" in sys.argv:
        sys.argv.remove("--serve")
        app.main()
    else:
        run()
