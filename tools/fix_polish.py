"""
Poprawia polskie słowa zapisane bez znaków diakrytycznych.

Dopasowuje CAŁE wyrazy (granice słów), więc nie psuje wyrazów dłuższych:
"pytan" -> "pytań", ale "pytania" pozostaje bez zmian. Odtwarza wielkość
liter: "zrodlo" -> "źródło", "Zrodlo" -> "Źródło", "PODGLAD" -> "PODGLĄD".

    python tools/fix_polish.py --dry    # pokaż, co się zmieni
    python tools/fix_polish.py          # zastosuj
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polish_words import WORD_MAP, NEVER_TOUCH  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTS = {".py", ".js", ".css", ".html", ".md", ".ps1", ".bat", ".sh", ".json"}
SKIP_DIRS = {".git", "build", "dist", "__pycache__", "karty", "media",
             ".venv", "tools", "vendor"}

PATTERN = re.compile(
    r"\b(" + "|".join(sorted(WORD_MAP, key=len, reverse=True)) + r")\b",
    re.IGNORECASE)


def restore_case(src, repl):
    if src.isupper() and len(src) > 1:
        return repl.upper()
    if src[:1].isupper():
        return repl[:1].upper() + repl[1:]
    return repl


def fix_text(text):
    count = 0

    def sub(m):
        nonlocal count
        word = m.group(0)
        if word.lower() in NEVER_TOUCH:
            return word
        count += 1
        return restore_case(word, WORD_MAP[word.lower()])

    return PATTERN.sub(sub, text), count


def iter_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if os.path.splitext(f)[1].lower() in EXTS:
                yield os.path.join(base, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    total, touched = 0, []
    for path in iter_files():
        try:
            text = open(path, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        fixed, n = fix_text(text)
        if n:
            total += n
            touched.append((os.path.relpath(path, ROOT), n))
            if not args.dry:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(fixed)

    for rel, n in sorted(touched, key=lambda x: -x[1]):
        print(f"  {rel}: {n}")
    print(f"\n{'PROBNIE: ' if args.dry else ''}{total} poprawek w {len(touched)} plikach")


if __name__ == "__main__":
    main()
