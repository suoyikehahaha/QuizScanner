# Instalacja i obsługa QuizScanner — krok po kroku

Ten przewodnik prowadzi za rękę od pobrania pliku do przeprowadzenia
pierwszego quizu. Wybierz swój system.

---

## A. Windows — najprościej (plik `.exe`, bez instalowania niczego)

### 1. Pobierz program
1. Wejdź na stronę **Releases** repozytorium:
   `https://github.com/PiotrKajor/QuizScanner/releases`
2. W najnowszym wydaniu, w sekcji **Assets**, kliknij plik
   **`QuizScanner-v…​.exe`** (nazwa zawiera numer wersji, np. `QuizScanner-v1.3.0.exe`).
3. Plik (~67 MB) trafi do folderu **Pobrane**.

> Repozytorium jest prywatne — pobrać może tylko zalogowany właściciel konta.
> Aby udostępnić program innym nauczycielom, wyślij im pobrany plik `.exe`
> bezpośrednio albo zmień repozytorium na publiczne.

### 2. Przenieś plik w dobre miejsce
Przenieś pobrany plik `.exe` na **Pulpit** lub do **Dokumentów**.
Program zapisuje quizy i wyniki **obok siebie**, więc nie umieszczaj go w
`C:\Program Files` (tam nie ma prawa zapisu).

### 3. Uruchom (pierwszy raz)
1. Kliknij dwukrotnie pobrany plik **`.exe`**.
2. Pojawi się okno Windows **„System Windows ochronił Twój komputer"**
   (bo program nie jest podpisany certyfikatem — to normalne dla darmowych aplikacji).
   Kliknij **„Więcej informacji"** → **„Uruchom mimo to"**.
3. Po chwili (pierwsze uruchomienie ~5–10 s) otworzy się małe okno **QuizScanner**.

> Jeśli antywirus zablokuje plik (fałszywy alarm zdarza się programom z
> PyInstaller), dodaj pobrany plik `.exe` do wyjątków / „Zezwól na urządzeniu".

### 4. Włącz aplikację
1. W oknie kliknij **„▶ Uruchom"**.
2. Windows zapyta o **zaporę sieciową** — zaznacz **„Sieci prywatne"** i kliknij
   **„Zezwól na dostęp"** (potrzebne, by tablicę dało się otworzyć na innym
   urządzeniu w sieci; do pracy na jednym komputerze też kliknij Zezwól).
3. Automatycznie otworzy się przeglądarka z **panelem nauczyciela**.

Gotowe. Przejdź do sekcji **[Pierwszy quiz](#pierwszy-quiz)**.

---

## B. Linux / macOS (potrzebny Python)

Plik `.exe` działa tylko na Windows. Na Linux/macOS instaluje się ze źródeł.

### 1. Pobierz projekt
- Na stronie repozytorium: **Code → Download ZIP**, rozpakuj.
- Albo w terminalu: `git clone https://github.com/PiotrKajor/QuizScanner.git`

### 2. Zainstaluj
W terminalu, w folderze projektu:
```bash
chmod +x install.sh
./install.sh
```
Skrypt utworzy środowisko `.venv`, zainstaluje zależności i przygotuje `start.sh`.

Jeśli brakuje Pythona:
- **Ubuntu/Debian:** `sudo apt install python3 python3-venv python3-pip`
- **Fedora:** `sudo dnf install python3 python3-pip`
- **macOS:** `brew install python`

### 3. Uruchom
```bash
./start.sh
```
Otworzy się przeglądarka z panelem nauczyciela. Inna kamera: `./start.sh --camera 1`.

---

## C. Windows ze źródeł (alternatywa dla `.exe`)

Jeśli wolisz nie używać gotowego pliku: zainstaluj Pythona z
[python.org](https://www.python.org/downloads/) (zaznacz **„Add Python to PATH"**),
potem dwuklik w **`install-windows.bat`**. Po instalacji uruchamiaj przez
**`Uruchom.bat`** lub `python launcher.py`.

---

## Pierwszy quiz

### 1. Przygotuj pytania
W panelu nauczyciela kliknij **„✏️ Edytor"**. Możesz użyć gotowego
`Przykładowy quiz` albo utworzyć własny (tytuł, pytania, 4 odpowiedzi,
zaznacz poprawną, ustaw czas i punkty). Zapisz.

### 2. Wpisz uczniów i pobierz karty
1. W edytorze, zakładka **„Uczniowie"** — wpisz listę klasy. **ID = numer na
   karcie** ucznia.
2. Kliknij **„📄 Pobierz karty (PDF)"**. Pobierze się gotowy plik PDF z osobną
   kartą dla każdego ucznia (jedna karta na stronę A4). Wydrukuj i rozdaj.
   **Działa też z `.exe`** — nie trzeba Pythona.

> **Gotowy przykładowy zestaw** 40 kart (bez imion, numery 0–39) jest też do
> pobrania w [Releases](https://github.com/PiotrKajor/QuizScanner/releases)
> jako `karty_przykladowe_40.pdf`.
>
> Wersja ze źródeł ma dodatkowo skrypt:
> `python generate_cards.py --names students.csv` (tworzy PNG + `karty.pdf`).

### 2b. Nie masz kamery? Użyj telefonu
1. Zainstaluj w telefonie **IP Webcam** (Android) albo **Iriun Webcam** /
   **DroidCam** (Android i iPhone) — wszystkie są darmowe.
2. Podłącz telefon do **tej samej sieci Wi‑Fi** co komputer.
3. W aplikacji telefonu wybierz „Start server" — pokaże adres, np.
   `http://192.168.1.50:8080`.
4. W panelu nauczyciela, w polu **Źródło obrazu**, wpisz adres strumienia
   (`http://192.168.1.50:8080/video`) i kliknij **Przełącz**.

W panelu jest też przycisk **„📱 Jak podłączyć telefon?"** z tą instrukcją.

### 3. Przeprowadź quiz
1. Na rzutniku otwórz **Tablicę** (przycisk „📺 Tablica" albo adres
   `http://localhost:8000/board`).
2. W panelu nauczyciela: **„▶ Start pytania"**.
3. Uczniowie podnoszą karty, obracając **wybraną literę (A/B/C/D) do góry**.
   Kamera odczytuje wszystkich naraz — na żywo widać, ile osób odpowiedziało.
4. **„✓ Pokaż wynik"** — tablica pokazuje poprawną odpowiedź i rozkład, punkty
   się naliczają.
5. **„Następne ▶"** — kolejne pytanie. Po ostatnim pojawia się ranking.

**Punkty za szybkość** (przełącznik w panelu): domyślnie **wyłączone** —
każda poprawna odpowiedź warta tyle samo. Włącz, jeśli chcesz, by szybsza
odpowiedź dawała więcej.

**Tryb automatyczny** (przełącznik w panelu): włącz go, a po starcie quiz
prowadzi się sam — odlicza czas, pokazuje wynik, przechodzi do następnego
pytania i na koniec wyświetla ranking. Nie musisz nic klikać. Czasy
(ile pokazywać wynik, jaka przerwa) ustawisz w edytorze, w sekcji
**Ustawienia quizu**.

### 4. Dodatkowe możliwości

| Chcę… | Gdzie |
|---|---|
| Zmienić język na angielski | Lista wyboru języka na górze panelu (dotyczy też tablicy) |
| Dodać zdjęcie lub film do pytania | Edytor → pytanie → **🖼 Dodaj plik** |
| Wysłać quiz innemu nauczycielowi | Edytor → **⬇ Zapisz do pliku** (plik `.quiz` zawiera też media) |
| Wczytać cudzy quiz | Edytor → **⬆ Wczytaj z pliku** |
| Wylosować kolejność pytań/odpowiedzi | Edytor → **Ustawienia quizu** |
| Uniknąć fałszywych odczytów z tła | Panel → **Tylko uczniowie z listy** (domyślnie włączone) |

---

## Rozwiązywanie problemów

| Problem | Rozwiązanie |
|---|---|
| „System Windows ochronił Twój komputer" | „Więcej informacji" → „Uruchom mimo to". Program jest niepodpisany, to normalne. |
| Antywirus usuwa `.exe` | Dodaj do wyjątków. To fałszywy alarm typowy dla PyInstaller. |
| „Kamera niedostępna" | Inny numer kamery w oknie (0/1/2). Windows: Ustawienia → Prywatność → Kamera → zezwól aplikacjom klasycznym. |
| Kamera nie czyta kart | Lepsze światło, matowy papier bez folii, karta zwrócona płasko do kamery (nie pod ostrym kątem). |
| Czyta tylko niektóre karty | Błąd naprawiony w wersji **1.3.0** (odbicie lustrzane psuło rozpoznawanie markerów). Pobierz najnowszy plik z Releases. |
| Tablica nie otwiera się na innym urządzeniu | Użyj adresu „Tablica w sieci" z panelu; oba urządzenia w tej samej sieci Wi-Fi; w zaporze zezwól na sieci prywatne. |
| „Nie udało się uruchomić na porcie" | Port zajęty — wpisz w oknie inny (np. 8080). |
| Nie zapisują się quizy / wyniki | Przenieś `.exe` do folderu z prawem zapisu (Pulpit, Dokumenty), nie do `Program Files`. |
| Pierwsze uruchomienie długo trwa | Jednoplikowy `.exe` rozpakowuje się przy starcie (kilka sekund). Kolejne uruchomienia są tak samo szybkie. |

Gdzie są dane: quizy w folderze `quizzes/`, lista uczniów `students.csv`,
wyniki `wyniki_<data>.csv` — wszystko **obok** pliku programu (`.exe`).
