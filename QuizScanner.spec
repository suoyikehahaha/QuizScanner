# Reproducible Windows build with the bundled Tcl/Tk runtime.
from pathlib import Path
import re

base = Path(SPECPATH)
runtime = base / ".python-runtime" / "cpython-3.12.13-windows-x86_64-none"
version = re.search(r'VERSION\s*=\s*"([^"]+)"', (base / "quizscanner/__init__.py").read_text(encoding="utf-8")).group(1)
tk_binaries = [(str(runtime / "DLLs" / name), ".") for name in ("_tkinter.pyd", "tcl86t.dll", "tk86t.dll")] if runtime.exists() else []
tk_data = [(str(runtime / "tcl/tcl8.6"), "_tcl_data"), (str(runtime / "tcl/tk8.6"), "_tk_data"), (str(runtime / "tcl/tcl8"), "tcl8")] if runtime.exists() else []
a = Analysis(
    [str(base / "launcher.py")], pathex=[str(base)],
    binaries=tk_binaries,
    datas=[(str(base / "assets/logo.ico"), "assets"), (str(base / "quizscanner/web"), "web"),
           (str(base / "data/quizzes"), "data/quizzes"), (str(base / "data/students.csv"), "data"),
           ] + tk_data,
    hiddenimports=["tkinter", "_tkinter", "quizscanner.cards", "quizscanner.aruco", "quizscanner.report", "quizscanner.storage"],
    hookspath=[str(base / "tools/pyinstaller_hooks")] if runtime.exists() else [], runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name=f"QuizScanner-简体中文版-班级与安卓教师端-{version}", console=False,
          debug=False, strip=False, upx=False, icon=str(base / "assets/logo.ico"))
