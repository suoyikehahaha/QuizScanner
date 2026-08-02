"""
Kontrola tekstu: wyszukuje polskie słowa zapisane bez znaków diakrytycznych
(np. "zrodlo" zamiast "źródło").

Korzysta z tego samego słownika co tools/fix_polish.py i dopasowuje CAŁE
wyrazy, więc "pytania" nie jest zgłaszane tylko dlatego, że zawiera "pytan".

    python tools/check_polish.py            # raport
    python tools/check_polish.py --files    # same nazwy plików

Kod wyjścia: 0 gdy czysto, 1 gdy coś znaleziono (nadaje się do CI).
"""

import argparse
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polish_words import WORD_MAP, NEVER_TOUCH  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTS = {".py", ".js", ".css", ".html", ".md", ".ps1", ".bat", ".sh", ".json"}
# Folder tools/ zawiera słownik z formami bez ogonków — z założenia.
SKIP_DIRS = {".git", "build", "dist", "__pycache__", "karty", "media",
             ".venv", "tools"}

PATTERN = re.compile(
    r"\b(" + "|".join(sorted(WORD_MAP, key=len, reverse=True)) + r")\b",
    re.IGNORECASE)


def iter_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if os.path.splitext(f)[1].lower() in EXTS:
                yield os.path.join(base, f)


def find_issues(text):
    """Zwraca listę (numer linii, słowo, propozycja, fragment linii)."""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        # Furtka na wyjątki: linia z "polish-ok" nie jest sprawdzana
        # (np. lista funkcji trygonometrycznych, gdzie "cos" to cosinus).
        if "polish-ok" in line:
            continue
        for m in PATTERN.finditer(line):
            word = m.group(0)
            if word.lower() in NEVER_TOUCH:
                continue
            out.append((i, word, WORD_MAP[word.lower()], line.strip()[:80]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", action="store_true",
                    help="pokaż tylko nazwy plików")
    args = ap.parse_args()

    # Wynik wypisujemy w UTF-8 niezależnie od strony kodowej konsoli.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    total, per_file = 0, {}
    for path in iter_files():
        try:
            text = open(path, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        issues = find_issues(text)
        if issues:
            per_file[os.path.relpath(path, ROOT)] = issues
            total += len(issues)

    for rel in sorted(per_file, key=lambda k: -len(per_file[k])):
        print(f"{rel}: {len(per_file[rel])}")
        if not args.files:
            for line, bad, good, snippet in per_file[rel][:5]:
                print(f"    {line:>4}: {bad} -> {good}   | {snippet}")

    if total:
        print(f"\nZnaleziono {total} miejsc w {len(per_file)} plikach.")
        print("Napraw poleceniem: python tools/fix_polish.py")
        return 1
    print("Czysto — wszystkie polskie słowa mają znaki diakrytyczne.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
