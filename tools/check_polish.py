"""
Kontrola jakości tekstu: wyszukuje polskie słowa zapisane bez znaków
diakrytycznych (np. "zrodlo" zamiast "źródło") w plikach projektu.

Uruchomienie:
    python tools/check_polish.py            # raport
    python tools/check_polish.py --fix      # automatyczna poprawa

Skrypt celowo pomija identyfikatory kodu (nazwy zmiennych i funkcji są po
angielsku) oraz nazwy plików, które muszą pozostać w ASCII.
"""

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Rozszerzenia, które sprawdzamy.
EXTS = {".py", ".js", ".css", ".html", ".md", ".ps1", ".bat", ".sh", ".json", ".csv"}
SKIP_DIRS = {".git", "build", "dist", "__pycache__", "karty", "media", ".venv"}

# Słowa, które MUSZĄ zostać w ASCII (nazwy plików, klucze, polecenia).
PROTECTED = [
    "przyklad.json", "przyklad", "wyniki_", "karty.pdf", "karty/",
    "QuizScanner", "quizscanner",
]

# Mapa: forma bez znaków -> forma poprawna. Kolejność ma znaczenie
# (dłuższe formy najpierw), żeby nie psuć dłuższych słów.
WORDS = [
    ("Zatrzymywanie", "Zatrzymywanie"),  # bez zmian, kotwica
    ("wspolrzedn", "współrzędn"), ("wspolczyn", "współczyn"), ("wspoln", "wspóln"),
    ("nastepstw", "następstw"), ("nastepn", "następn"), ("nastepu", "następu"),
    ("poprzedni", "poprzedni"),
    ("odpowiedzi", "odpowiedzi"), ("odpowiedz", "odpowiedź"),
    ("zrodlow", "źródłow"), ("zrodl", "źródł"), ("zrodel", "źródeł"),
    ("wlasciw", "właściw"), ("wlasn", "własn"), ("wlacz", "włącz"), ("wlaczo", "włączo"),
    ("wylacz", "wyłącz"),
    ("dziala", "działa"), ("dzialan", "działan"), ("dzialaj", "działaj"),
    ("kolejnosc", "kolejność"), ("kolejnosci", "kolejności"),
    ("polacze", "połącze"), ("polaczo", "połączo"), ("polacz", "połącz"),
    ("obsluguj", "obsługuj"), ("obslug", "obsług"),
    ("wiec ", "więc "), ("wiecej", "więcej"),
    ("ktore", "które"), ("ktora", "która"), ("ktory", "który"),
    ("ktorych", "których"), ("ktorym", "którym"), ("ktorej", "której"),
    ("moze", "może"), ("mozna", "można"), ("mozliw", "możliw"),
    ("czesc", "część"), ("czesci", "części"), ("czest", "częst"),
    ("wyswietl", "wyświetl"),
    ("bledn", "błędn"), ("bledow", "błędów"), ("blad", "błąd"), ("bledy", "błędy"),
    ("blednie", "błędnie"), ("bledu", "błędu"),
    ("recznie", "ręcznie"), ("reczn", "ręczn"),
    ("sciezk", "ścieżk"),
    ("uzytkownik", "użytkownik"), ("uzyc", "użyć"), ("uzywa", "używa"),
    ("uzyj", "użyj"), ("uzycie", "użycie"),
    ("jezyk", "język"), ("jezyc", "języc"),
    ("wybran", "wybran"),
    ("srodek", "środek"), ("srodk", "środk"), ("srodowisk", "środowisk"),
    ("zadan", "żadan"), ("zaden", "żaden"),
    ("wiekszo", "większo"), ("wieksz", "większ"),
    ("mniejsz", "mniejsz"),
    ("dlugo", "długo"), ("dlug", "dług"),
    ("krotk", "krótk"), ("skrot", "skrót"),
    ("pomoc", "pomoc"),
    ("obrot", "obrót"), ("obroc", "obróć"), ("obraca", "obraca"),
    ("gory", "góry"), ("gorn", "górn"),
    ("dol ", "dół "), ("doln", "doln"),
    ("liter", "liter"),
    ("wydruk", "wydruk"), ("drukow", "drukow"),
    ("ustawien", "ustawień"), ("ustawie", "ustawie"),
    ("domyslni", "domyślni"), ("domysln", "domyśln"),
    ("bezpiecz", "bezpiecz"),
    ("zapisz", "zapisz"), ("zapisu", "zapisu"),
    ("wczyta", "wczyta"),
    ("stron", "stron"),
    ("pytan", "pytań"), ("pytania", "pytania"), ("pytanie", "pytanie"),
    ("uczen", "uczeń"), ("uczni", "uczni"),
    ("punkt", "punkt"),
    ("czas", "czas"),
    ("swiat", "świat"), ("swietl", "świetl"),
    ("zamkni", "zamkni"), ("zamyka", "zamyka"),
    ("sprawdz", "sprawdź"), ("sprawdza", "sprawdza"),
    ("przeglada", "przeglądа"),
    ("wylapy", "wyłapy"),
    ("smieci", "śmieci"),
    ("falszyw", "fałszyw"),
    ("znaczk", "znaczk"),
    ("przelacz", "przełącz"),
    ("opoznien", "opóźnień"), ("opoznie", "opóźnie"),
    ("losow", "losow"),
    ("przerw", "przerw"),
    ("konc", "końc"), ("koncz", "kończ"),
    ("wynik", "wynik"),
    ("zaleznos", "zależnoś"), ("zalezn", "zależn"),
    ("potrzeb", "potrzeb"),
    ("brakuj", "brakuj"),
    ("instrukcj", "instrukcj"),
    ("aplikacj", "aplikacj"),
    ("przypadk", "przypadk"),
    ("wywola", "wywoła"), ("wywolu", "wywołu"),
    ("ostatecz", "ostatecz"),
    ("awaryjn", "awaryjn"),
    ("podglad", "podgląd"), ("podgladu", "podglądu"),
    ("zeby", "żeby"), ("zebys", "żebyś"),
    ("juz ", "już "),
    ("jesli", "jeśli"),
    ("wszystk", "wszystk"),
    ("ramk", "ramk"),
    ("plyn", "płyn"),
    ("male ", "małe "), ("maly", "mały"), ("mala", "mała"),
    ("duzy", "duży"), ("duza", "duża"), ("duze", "duże"),
    ("pozostal", "pozostał"),
    ("dolacz", "dołącz"),
    ("wysyla", "wysyła"), ("wyslij", "wyślij"),
    ("odczyt", "odczyt"),
    ("wykryc", "wykryć"), ("wykrywa", "wykrywa"),
    ("czarno-bial", "czarno-biał"), ("bialy", "biały"), ("biale", "białe"),
    ("bialym", "białym"), ("bial", "biał"),
    ("czarn", "czarn"),
    ("kolejk", "kolejk"),
    ("watek", "wątek"), ("watk", "wątk"),
    ("petla", "pętla"), ("petli", "pętli"),
    ("slownik", "słownik"),
    ("wartosc", "wartość"), ("wartosci", "wartości"),
    ("zgodn", "zgodn"),
    ("stabiln", "stabiln"),
    ("odleglos", "odległoś"),
    ("kat ", "kąt "), ("katy", "kąty"), ("katow", "kątów"),
    ("zamrozon", "zamrożon"),
    ("rozpakow", "rozpakow"),
    ("wgrywa", "wgrywa"), ("wgra", "wgra"),
    ("osadzon", "osadzon"),
]


def iter_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if os.path.splitext(f)[1].lower() in EXTS:
                yield os.path.join(base, f)


def find_issues(text):
    """Zwraca listę (linia, słowo bez znaków, propozycja)."""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        if any(p.lower() in low for p in PROTECTED):
            continue
        for bad, good in WORDS:
            if bad == good:
                continue
            for m in re.finditer(re.escape(bad), line, re.IGNORECASE):
                out.append((i, bad, good, line.strip()[:90]))
                break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-files", action="store_true")
    args = ap.parse_args()

    total = 0
    per_file = {}
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
        print(f"{rel}: {len(per_file[rel])} miejsc")
        if args.list_files:
            continue
        for line, bad, good, snippet in per_file[rel][:4]:
            print(f"    {line:>4}: {bad} -> {good}   | {snippet}")
    print(f"\nRAZEM: {total} miejsc w {len(per_file)} plikach")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
