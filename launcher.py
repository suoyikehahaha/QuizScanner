"""
QuizScanner 桌面启动器（控制台）

在同一进程线程中启动 Web 应用服务，支持源码模式 (python launcher.py)
以及 PyInstaller 单文件打包 (QuizScanner.exe)。
提供教师面板、大屏、题目编辑器的一键启动与连接指引。
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

# 启用 Windows 高分屏 (High-DPI) 适配，防止界面模糊
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

from quizscanner import server as app
from quizscanner import VERSION
from quizscanner.paths import ICON_ICO


class Launcher:
    def __init__(self, root):
        self.root = root
        self.httpd = None
        self.thread = None
        self.external_server = False
        self.external_port = None

        root.title("QuizScanner 课堂答题系统")
        try:
            root.iconbitmap(ICON_ICO)
        except Exception:
            pass

        root.geometry("540x510")
        root.resizable(False, False)
        root.configure(bg="#121620")

        # 头部标题
        header_frame = tk.Frame(root, bg="#121620")
        header_frame.pack(pady=(22, 10))

        tk.Label(
            header_frame, text="QuizScanner 课堂答题系统",
            font=("Microsoft YaHei UI", 18, "bold"),
            fg="#f26e4e", bg="#121620"
        ).pack()

        tk.Label(
            header_frame, text=f"随堂测验 · 纸质答题卡极速扫码 · v{VERSION}",
            font=("Microsoft YaHei UI", 9),
            fg="#8c97b2", bg="#121620"
        ).pack(pady=(3, 0))

        # 参数配置卡片
        card_cfg = tk.Frame(root, bg="#1c2233", padx=16, pady=10, relief="flat", highlightthickness=1, highlightbackground="#2d3752")
        card_cfg.pack(fill="x", padx=36, pady=(0, 12))

        tk.Label(card_cfg, text="摄像头编号：", font=("Microsoft YaHei UI", 9), fg="#e2e8f5", bg="#1c2233").grid(row=0, column=0, padx=6, sticky="e")
        self.cam = tk.Spinbox(card_cfg, from_=0, to=8, width=5, font=("Consolas", 10), justify="center", bg="#121620", fg="#ffffff", insertbackground="white", relief="flat")
        self.cam.grid(row=0, column=1, padx=6)

        tk.Label(card_cfg, text="服务端口：", font=("Microsoft YaHei UI", 9), fg="#e2e8f5", bg="#1c2233").grid(row=0, column=2, padx=(18, 6), sticky="e")
        self.port = tk.Entry(card_cfg, width=7, font=("Consolas", 10), justify="center", bg="#121620", fg="#ffffff", insertbackground="white", relief="flat")
        self.port.insert(0, "8012")
        self.port.grid(row=0, column=3, padx=6)

        # 核心主按钮：启动 / 停止服务
        self.startBtn = tk.Button(
            root, text="▶  启动课堂服务",
            bg="#2da44e", fg="#ffffff", activebackground="#278c43", activeforeground="#ffffff",
            font=("Microsoft YaHei UI", 11, "bold"), relief="flat",
            padx=20, pady=8, cursor="hand2", command=self.toggle
        )
        self.startBtn.pack(pady=4)

        # 运行状态卡片
        self.statusCard = tk.Frame(root, bg="#1a2030", padx=14, pady=8, relief="flat", highlightthickness=1, highlightbackground="#2b344c")
        self.statusCard.pack(fill="x", padx=36, pady=8)

        self.statusDot = tk.Label(self.statusCard, text="●", font=("Segoe UI", 11), fg="#6e7891", bg="#1a2030")
        self.statusDot.pack(side="left", padx=(0, 8))

        self.status = tk.Label(
            self.statusCard, text="服务未启动，点击上方按钮开始",
            font=("Microsoft YaHei UI", 9), fg="#8c97b2", bg="#1a2030", wraplength=410, justify="left"
        )
        self.status.pack(side="left", fill="x", expand=True)

        # 快捷功能入口磁贴（三个大按钮）
        links_frame = tk.Frame(root, bg="#121620")
        links_frame.pack(fill="x", padx=36, pady=10)

        self.b_teacher = self._action_button(links_frame, "🎛  教师控制台", "teacher", 0)
        self.b_board = self._action_button(links_frame, "📺  投影大屏", "board", 1)
        self.b_editor = self._action_button(links_frame, "✏️  题库与名单管理", "editor", 2)
        self._set_links(False)

        # 辅助功能行（热点设置与手机连接帮助）
        aux_frame = tk.Frame(root, bg="#121620")
        aux_frame.pack(fill="x", padx=36, pady=(6, 0))

        self.hotspotBtn = tk.Button(
            aux_frame, text="📶 打开电脑移动热点设置",
            bg="#202738", fg="#9aa7c4", activebackground="#293247", activeforeground="#ffffff",
            font=("Microsoft YaHei UI", 8), relief="flat", padx=10, pady=5, cursor="hand2",
            command=self.open_hotspot_settings
        )
        self.hotspotBtn.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.connectionHelpBtn = tk.Button(
            aux_frame, text="📱 手机无法连接？查看帮助",
            bg="#202738", fg="#9aa7c4", activebackground="#293247", activeforeground="#ffffff",
            font=("Microsoft YaHei UI", 8), relief="flat", padx=10, pady=5, cursor="hand2",
            command=self.show_connection_help
        )
        self.connectionHelpBtn.pack(side="right", expand=True, fill="x", padx=(5, 0))

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _action_button(self, parent, text, path, col):
        btn = tk.Button(
            parent, text=text,
            relief="flat", bg="#202738", fg="#dce3f5",
            activebackground="#2e3852", activeforeground="#ffffff",
            disabledforeground="#4b556e",
            font=("Microsoft YaHei UI", 9, "bold"),
            padx=8, pady=9, cursor="hand2",
            command=lambda: self.open(path)
        )
        parent.columnconfigure(col, weight=1)
        btn.grid(row=0, column=col, padx=4, sticky="ew")
        return btn

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
            text = f"服务正常运行中 · 手机连电脑热点访问：http://{address}:{port}/mobile"
        elif addresses:
            text = f"服务正常运行中 · 手机连同一 Wi-Fi 访问：http://{address}:{port}/mobile"
        else:
            text = "服务正常运行中 · 未发现局域网网卡，可在本机浏览器打开大屏与教师面板"

        self.statusDot.config(text="●", fg="#3fb950")
        self.status.config(text=text, fg="#3fb950")
        if not hotspot_ip and not addresses and sys.platform == "win32":
            self.root.after(1200, self.open_hotspot_settings)

    def open_hotspot_settings(self):
        if sys.platform != "win32":
            messagebox.showinfo("移动热点", "请在系统网络设置中开启移动热点。")
            return
        try:
            os.startfile("ms-settings:network-mobilehotspot")
        except OSError as e:
            messagebox.showerror("移动热点", f"无法自动打开移动热点设置页面。\n\n{e}")

    def show_connection_help(self):
        port = self.external_port or self.port.get().strip() or "8012"
        addresses = app.lan_ips()
        urls = "\n".join(f"http://{address}:{port}/mobile" for address in addresses[:6])
        if not urls:
            urls = f"启动服务并将电脑连接至网络后，此处会自动显示局域网地址。端口：{port}"
        messagebox.showinfo(
            "手机连接 QuizScanner 指南",
            "电脑无法开启移动热点时，完全不影响使用：\n\n"
            "1. 让电脑与手机连接到同一个路由器的 Wi-Fi（电脑使用网线连接同一路由器亦可）；\n"
            "2. 在手机教师端 APK 中扫描教师面板上的二维码，或在手机浏览器中输入以下地址：\n"
            f"{urls}\n\n"
            "提示：请避免连接隔离设备的访客 Wi-Fi，并确保 Windows 防火墙允许 QuizScanner 通过专有网络。",
        )

    def start(self):
        port_str = self.port.get().strip() or "8012"
        try:
            port = int(port_str)
        except ValueError:
            port = 8012

        existing = self._existing_server(port)
        if existing:
            if existing.get("version") != VERSION:
                running_version = existing.get("version") or "未知"
                self.statusDot.config(text="▲", fg="#d29922")
                self.status.config(
                    text=f"端口 {port} 正在运行旧版 QuizScanner {running_version}，请更换端口或关闭旧版",
                    fg="#d29922",
                )
                messagebox.showwarning(
                    "检测到其他服务版本",
                    f"端口 {port} 上已有正在运行的 QuizScanner {running_version}。\n"
                    "请先关闭旧版本，或将端口修改为其他未占用端口后再启动。",
                )
                return
            self.external_server = True
            self.external_port = port
            self.port.config(state="disabled")
            self.startBtn.config(text="打开教师控制台", bg="#1f6feb", activebackground="#1a5cbf")
            self._set_links(True)
            self._set_running_status(port, existing)
            self.root.after(800, lambda: self.open("teacher"))
            return

        self.external_server = False
        self.external_port = None
        self.port.config(state="normal")
        try:
            cam = int(self.cam.get().strip() or "0")
        except ValueError:
            cam = 0

        try:
            self.httpd = app.build_server(camera=cam, port=port, host="0.0.0.0")
        except OSError as e:
            messagebox.showerror(
                "服务启动失败",
                f"无法在端口 {port} 启动服务。\n"
                f"可能端口已被其他程序占用，请更换端口重试。\n\n{e}"
            )
            self.httpd = None
            return

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.startBtn.config(text="■  停止课堂服务", bg="#da3633", activebackground="#b62324")
        self._set_links(True)
        self._set_running_status(port)
        self.root.after(800, lambda: self.open("teacher"))

    def stop(self):
        if self.httpd:
            app.stop_server(self.httpd)
            self.httpd = None
        self.startBtn.config(text="▶  启动课堂服务", bg="#2da44e", activebackground="#278c43")
        self.startBtn.config(command=self.toggle)
        self.port.config(state="normal")
        self.external_server = False
        self.external_port = None
        self._set_links(False)
        self.statusDot.config(text="●", fg="#6e7891")
        self.status.config(text="服务未启动，点击上方按钮开始", fg="#8c97b2")

    def open(self, path):
        port = self.external_port or self.port.get().strip() or "8012"
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
    if "--serve" in sys.argv:
        sys.argv.remove("--serve")
        app.main()
    else:
        run()
