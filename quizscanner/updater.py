"""
Automatyczna aktualizacja aplikacji (wydania z GitHuba).

Dwa kroki, oba wywoływane z panelu nauczyciela:

  check()   -- pyta API GitHuba o najnowsze wydanie i porównuje z VERSION;
               wynik jest zapamiętywany, żeby nie pytać przy każdym odświeżeniu,
  apply()   -- pobiera plik wydania i podmienia działający program.

Podmiana działa tylko dla wersji spakowanej w .exe: Windows nie pozwala
nadpisać uruchomionego pliku, więc pobrany plik zapisujemy obok, a wymiany
dokonuje mały skrypt .bat uruchamiany przy zamykaniu programu. Przy pracy ze
źródeł aktualizacją jest `git pull` -- wtedy tylko informujemy o nowej wersji.
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request

from . import GITHUB_REPO, VERSION

API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"
CHECK_TTL = 6 * 3600          # jak długo trzymamy wynik sprawdzenia (s)
TIMEOUT = 8

_state = {"checked_at": 0, "result": None}
_lock = threading.Lock()


def version_tuple(v):
    """'v2.10.1' -> (2, 10, 1); brakujące człony to zera."""
    nums = [int(x) for x in re.findall(r"\d+", str(v or ""))[:3]]
    return tuple(nums + [0] * (3 - len(nums)))


def is_newer(remote, local=VERSION):
    return version_tuple(remote) > version_tuple(local)


def frozen():
    return bool(getattr(sys, "frozen", False))


def _fetch_latest():
    req = urllib.request.Request(API_URL, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"QuizScanner/{VERSION}",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)


def check(force=False):
    """Zwraca słownik ze stanem aktualizacji (nigdy nie rzuca wyjątkiem)."""
    with _lock:
        fresh = time.time() - _state["checked_at"] < CHECK_TTL
        if _state["result"] and fresh and not force:
            return _state["result"]

    result = {"current": VERSION, "latest": None, "update": False,
              "url": RELEASES_URL, "asset": None, "can_apply": False,
              "error": None}
    try:
        rel = _fetch_latest()
        tag = rel.get("tag_name") or rel.get("name") or ""
        result["latest"] = tag.lstrip("vV")
        result["url"] = rel.get("html_url") or RELEASES_URL
        result["notes"] = (rel.get("body") or "")[:2000]
        result["update"] = is_newer(tag)
        for a in rel.get("assets", []):
            if str(a.get("name", "")).lower().endswith(".exe"):
                result["asset"] = {"name": a["name"],
                                   "url": a["browser_download_url"],
                                   "size": a.get("size", 0)}
                break
        result["can_apply"] = bool(result["update"] and result["asset"] and frozen())
    except Exception as e:                      # brak sieci = brak aktualizacji
        result["error"] = str(e)

    with _lock:
        _state["checked_at"] = time.time()
        _state["result"] = result
    return result


def check_async(enabled=True):
    """Sprawdzenie w tle przy starcie -- nie opóźnia uruchomienia programu."""
    if enabled:
        threading.Thread(target=check, daemon=True).start()


def download(asset, dest_dir):
    """Pobiera plik wydania. Zwraca ścieżkę pobranego pliku."""
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, asset["name"])
    req = urllib.request.Request(asset["url"], headers={
        "User-Agent": f"QuizScanner/{VERSION}"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest + ".part", "wb") as f:
        while True:
            chunk = r.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
    os.replace(dest + ".part", dest)
    return dest


_SWAP_BAT = """@echo off
rem Wymiana pliku QuizScanner po zamknieciu starej wersji (tworzone automatycznie).
ping -n 4 127.0.0.1 >nul
del "{old}" >nul 2>&1
start "" "{new}"
del "%~f0" >nul 2>&1
"""


def apply(status=None):
    """Pobiera nowe wydanie i przygotowuje podmianę pliku programu.

    Zwraca słownik: ok / plik / czy trzeba zrestartować aplikacje.
    """
    info = status or check(force=True)
    if not info.get("update") or not info.get("asset"):
        return {"ok": False, "error": "暂无新版本"}
    if not frozen():
        # Ze źródeł nie podmieniamy plików -- to zadanie dla gita.
        return {"ok": False, "error": "source", "url": info["url"]}

    exe = os.path.abspath(sys.executable)
    new_path = download(info["asset"], os.path.dirname(exe))
    if os.path.abspath(new_path) == exe:        # ta sama nazwa pliku
        return {"ok": True, "file": new_path, "restart": False}

    bat = os.path.join(os.path.dirname(exe), "quizscanner_update.bat")
    with open(bat, "w", encoding="cp1250", errors="replace") as f:
        f.write(_SWAP_BAT.format(old=exe, new=new_path))
    return {"ok": True, "file": new_path, "restart": True, "script": bat}


def run_swap_script(script):
    """Uruchamia skrypt wymiany (wywoływane tuż przed zamknięciem programu)."""
    if script and os.path.exists(script):
        subprocess.Popen(["cmd", "/c", script], close_fds=True,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
