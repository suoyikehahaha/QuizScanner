# Zmiany

Format: [wersja] — co nowego z punktu widzenia nauczyciela.

## [3.0.0] — 2026-08-02

### Nowe

- **Przybornik matematyczny w edytorze** — paleta symboli w sześciu sekcjach
  (podstawowe, potęgi i ułamki, greka, zbiory i logika, geometria, analiza),
  szablony działające na zaznaczeniu (`√( )`, przedział, układ) oraz zamiana
  zaznaczonego fragmentu na indeks górny/dolny. Wzory to tekst Unicode, więc
  wyglądają tak samo w edytorze, na tablicy i w raporcie PDF.
- **Motyw ciemny jako domyślny + 6 kolejnych**: jasny, ocean, las, zachód
  słońca, cukierkowy i wysoki kontrast. Zmiana z panelu działa od razu również
  na tablicy — także gdy stoi na innym komputerze.
- **Dźwięki tablicy** — start pytania, odliczanie ostatnich pięciu sekund,
  koniec czasu, wynik i fanfara na podium. Generowane w przeglądarce (WebAudio),
  bez plików audio. Przełącznik i suwak głośności w panelu.
- **Raport po grze** — nowy przycisk **„📊 Raport"**: ranking, skuteczność
  każdego ucznia, odpowiedzi na każde pytanie, rozkład A/B/C/D i wskazanie
  najtrudniejszego pytania. Pobieranie w **PDF, Excelu (XLSX), CSV, HTML,
  JSON i TXT**.
- **Automatyczny zapis raportu** — po ostatnim pytaniu komplet HTML + CSV + JSON
  trafia sam do `data/raporty/`.
- **Automatyczna aktualizacja** — pasek z informacją o nowym wydaniu i pobranie
  jednym kliknięciem; w wersji `.exe` plik podmienia się przy zamykaniu programu.
  Sprawdzanie można wyłączyć.
- **FAQ** — [docs/FAQ.md](docs/FAQ.md) z odpowiedziami na pytania o karty,
  kamerę, wzory, raporty, prywatność i typowe kłopoty.
- **Test dymny** `tools/selftest.py` — sprawdza strony, API, karty PDF, cały
  przebieg quizu, wszystkie formaty raportu oraz kompletność tłumaczeń PL/EN.

### Zmiany

- **Nowa struktura katalogów**: kod w pakiecie `quizscanner/`, dane użytkownika
  w `data/`, dokumentacja w `docs/`, skrypty w `scripts/`. Serwer uruchamia się
  teraz przez `python -m quizscanner` (dawniej `python app.py`).
- Dane nauczyciela (quizy, media, lista uczniów, raporty, ustawienia) siedzą
  w jednym folderze `data/` obok programu — łatwiej je skopiować i zarchiwizować.
- Eksport wyników przeniesiony ze skromnego `wyniki_<data>.csv` do pełnego
  raportu (stary przycisk „⬇ Eksport wyników" zastąpił „📊 Raport").
- Kontrola polskich znaków obsługuje wyjątki w linii (`polish-ok`), dzięki czemu
  nazwy funkcji trygonometrycznych nie są zgłaszane jako literówki.
- Numer wersji do budowania `.exe` czytany jest z `quizscanner/__init__.py`,
  więc nie da się wydać pliku z nieaktualnym numerem.

## [2.0.1]

- Naprawa narzędzia kontroli polskich znaków, pełne diakrytyki w repozytorium.

## [2.0.0]

- Języki PL/EN, tryb automatyczny, zdjęcia i filmy w pytaniach, telefon jako kamera.

## [1.3.0]

- Naprawa: skaner nie wykrywał większości kart (odbicie lustrzane).

## [1.2.0]

- Logo aplikacji, dopracowana strona repozytorium, numer wersji w nazwie `.exe`.

## [1.1.0]

- Pobieranie kart do druku (PDF) z poziomu aplikacji.

## [1.0.0]

- Pierwsze wydanie: system quizowy z odczytem kart ArUco z kamery,
  jednoplikowy `QuizScanner.exe`.
