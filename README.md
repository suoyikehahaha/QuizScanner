<p align="center">
  <img src="assets/logo.svg" width="130" alt="QuizScanner">
</p>

<h1 align="center">QuizScanner</h1>

<p align="center">
  <b>Darmowy system quizowy z odczytem odpowiedzi z kamery.</b><br>
  Uczniowie podnoszą wydrukowane karty z markerami ArUco, a kamera odczytuje
  wszystkie odpowiedzi naraz — otwarta alternatywa dla Plickers.
</p>

<p align="center">
  <img alt="wersja" src="https://img.shields.io/badge/wersja-2.0.1-e2603f">
  <img alt="języki" src="https://img.shields.io/badge/j%C4%99zyk-PL%20%7C%20EN-2f9fb3">
  <img alt="platforma" src="https://img.shields.io/badge/platforma-Windows%20%7C%20Linux%20%7C%20macOS-2f9fb3">
  <img alt="python" src="https://img.shields.io/badge/Python-3.10%2B-4faa6a">
  <img alt="licencja" src="https://img.shields.io/badge/licencja-MIT-8a7bef">
  <img alt="serwer" src="https://img.shields.io/badge/serwer-czysty%20stdlib%20bez%20Flask-e8a13c">
</p>

---

## ✨ Funkcje

- 📷 **Odczyt z kamery** — jeden kadr wykrywa całą klasę naraz (markery ArUco).
- 📱 **Telefon zamiast kamery** — wystarczy darmowa aplikacja streamująca (IP Webcam, DroidCam, Iriun).
- ▶️ **Tryb automatyczny** — wciskasz Start, a quiz sam odsłania wyniki i przechodzi dalej.
- 🖥️ **Tablica na rzutnik** — własny motyw „Scan": pytanie, timer, rozkład odpowiedzi, podium.
- 🖼️ **Zdjęcia i filmy w pytaniach** — wgrywasz plik w edytorze, pokazuje się na tablicy.
- ✏️ **Edytor z ustawieniami** — czas, punkty, losowanie pytań i odpowiedzi, opóźnienia trybu auto.
- 📤 **Quiz jako plik** — zapisujesz `.quiz` (z osadzonymi mediami) i wysyłasz innemu nauczycielowi.
- 🌍 **Polski i angielski** — przełącznik języka wspólny dla panelu i tablicy.
- 🎯 **Odporność na fałszywe odczyty** — ignoruje kody spoza listy klasy i wzory bez czarno-białego kontrastu.
- 🖨️ **Karty do druku** — gotowy PDF jednym kliknięciem (także z `.exe`).
- 🏆 **Punktacja i ranking** — stała albo „za szybkość" (przełącznik w panelu).
- 🔌 **Offline, bez kont i limitów** — serwer na czystej bibliotece Pythona (bez Flask).
- 🪟 **Jeden plik `.exe`** na Windows — pobierasz i klikasz, bez instalowania Pythona.

## 📑 Spis treści

[Jak to działa](#jak-to-działa) · [Instalacja](#instalacja) ·
[Szybki start](#szybki-start-ze-źródeł) · [Widoki](#trzy-widoki-adresy) ·
[Sterowanie](#sterowanie-quizem-panel-nauczyciela) ·
[Wskazówki](#konfiguracja-i-wskazówki) · [Integracja](#integracja-we-własnym-kodzie)

## Jak to działa

- Każda karta ma jeden marker ArUco o unikalnym ID = konkretny uczeń.
- Krawędzie karty opisane są literami **A / B / C / D**.
- Uczeń obraca kartę tak, aby wybrana litera była **u góry**.
- Kamera w jednym kadrze wykrywa wielu uczniów, odczytuje ID i obrót → odpowiedź.
- Domyślnie każda poprawna odpowiedź warta jest tyle samo punktów. Punkty za
  szybkość (kto pierwszy, ten więcej) można włączyć przełącznikiem w panelu.
- Jest ranking i podium.

## Instalacja

- **Windows (najprościej):** pobierz plik **`QuizScanner-v…​.exe`** (nazwa z
  numerem wersji) z zakładki
  [Releases](https://github.com/PiotrKajor/QuizScanner/releases), przenieś na
  Pulpit i kliknij dwukrotnie. Bez instalowania Pythona.
- **Linux / macOS:** `./install.sh`, potem `./start.sh`.
- **Pełna instrukcja krok po kroku** (ze zrzutami sytuacji, zaporą, kamerą i
  rozwiązywaniem problemów): **[INSTALACJA.md](INSTALACJA.md)**.

## Szybki start (ze źródeł)

```bash
pip install -r requirements.txt      # tylko jeśli czegoś brakuje
```

1. **Uruchom aplikację** — dwuklik w `Uruchom.bat` (Windows) albo:

   ```bash
   python launcher.py
   ```

   Otworzy się okno: wybierasz kamerę i port, klikasz „Uruchom serwer".
   Można też pominąć launcher i wystartować serwer wprost:

   ```bash
   python app.py --camera 0 --port 8000
   ```

2. **Przygotuj pytania** — otwórz **Edytor** i utwórz quiz (albo użyj
   gotowego `Przykładowy quiz`). W zakładce **Uczniowie** wpisz listę klasy
   (ID = numer na karcie).

3. **Pobierz i wydrukuj karty** — w edytorze (zakładka Uczniowie) kliknij
   **„📄 Pobierz karty (PDF)"**: dostaniesz PDF z kartą dla każdego ucznia
   (jedna na stronę A4). Działa też w wersji `.exe`.

   Alternatywnie ze źródeł: `python generate_cards.py --names students.csv --out karty`
   (tworzy PNG + `karty/karty.pdf`).

4. **Prowadź quiz** — w **Panelu nauczyciela** wczytaj quiz i steruj:
   Start pytania → uczniowie podnoszą karty → Pokaż wynik → Następne.
   Na projektorze wyświetl **Tablicę**.

## Trzy widoki (adresy)

| Widok | Adres | Do czego |
|---|---|---|
| Panel nauczyciela | `http://localhost:8000/teacher` | podgląd kamery, sterowanie, wyniki na żywo |
| Tablica (rzutnik) | `http://localhost:8000/board` | duży ekran dla uczniów — pytanie, timer, ranking (własny motyw „Scan") |
| Edytor | `http://localhost:8000/editor` | tworzenie quizów i lista uczniów |

Tablicę można otworzyć **z innego urządzenia w tej samej sieci** (np. drugi
komputer podpięty do rzutnika albo Smart TV) pod adresem
`http://<IP-komputera>:8000/board` — dokładny adres pokazuje panel nauczyciela.

## Sterowanie quizem (panel nauczyciela)

- **▶ Start pytania** — otwiera zbieranie odpowiedzi (rusza timer).
- **✓ Pokaż wynik** — zamyka pytanie, pokazuje poprawną odpowiedź i nalicza punkty.
- **◀ / ▶** — poprzednie / następne pytanie (po ostatnim pojawia się podium).
- **⟲ Reset punktów** — nowa rozgrywka od zera.
- **⬇ Eksport wyników** — zapis rankingu do `wyniki_<data>.csv`.
- **Przełącznik „Punkty za szybkość"** — wył. (domyślnie): każda poprawna
  odpowiedź warta tyle samo; wł.: szybsza odpowiedź daje więcej punktów.
- **Przełącznik „Tryb automatyczny"** — po włączeniu quiz prowadzi się sam:
  czas pytania → wynik → następne pytanie → ranking. Bez klikania.
- **Przełącznik „Tylko uczniowie z listy"** — ignoruje kody spoza klasy
  (chroni przed przypadkowymi wykryciami w tle).
- **Źródło obrazu** — numer kamery albo adres telefonu; przycisk
  „Jak podłączyć telefon?" opisuje krok po kroku.

## Telefon jako kamera

Nie masz kamery internetowej? Wystarczy telefon:

1. Zainstaluj **IP Webcam** (Android) albo **Iriun Webcam** / **DroidCam** (Android, iPhone).
2. Podłącz telefon do **tej samej sieci Wi‑Fi** co komputer.
3. W aplikacji wybierz „Start server" — pokaże adres, np. `http://192.168.1.50:8080`.
4. W panelu nauczyciela wpisz adres strumienia i kliknij **Przełącz**:
   - IP Webcam: `http://192.168.1.50:8080/video`
   - DroidCam: `http://192.168.1.50:4747/video`

## Dzielenie się quizem

W edytorze **„⬇ Zapisz do pliku"** tworzy plik `.quiz` z pytaniami, ustawieniami
**i osadzonymi zdjęciami/filmami** — jeden plik, który wystarczy wysłać. Odbiorca
klika **„⬆ Wczytaj z pliku"** i ma gotowy quiz razem z mediami.

Poprawna odpowiedź jest **ukryta na tablicy** do momentu „Pokaż wynik".

## Pliki projektu

| Plik / folder | Rola |
|---|---|
| `launcher.py`, `Uruchom.bat` | natywne okno startowe |
| `app.py` | serwer HTTP (panel, tablica, edytor, API, strumień kamery) |
| `quiz_session.py` | stan sesji, fazy pytania, punktacja, ranking |
| `camera_worker.py` | wątek kamery + skaner ArUco zasilający sesję |
| `scanner.py` | silnik `QuizScanEngine` (+ samodzielne demo z kamery) |
| `aruco_common.py` | słownik ArUco i mapowanie krawędź → odpowiedź |
| `generate_cards.py` | generator kart PNG/PDF do druku |
| `web/` | strony i style (board / teacher / editor) |
| `quizzes/` | zapisane quizy (JSON) |
| `students.csv` | lista uczniów (id,imię) do druku kart |

## Konfiguracja i wskazówki

- **Kamera:** `--camera 1` jeśli masz kilka. Na Windows używany jest szybki
  backend DirectShow (kamera startuje w ~2 s).
- **Zasięg:** marker ~8–10 cm czyta się z 4–6 m dobrą kamerą HD. Za mały
  marker lub słabe światło = brak odczytu. Drukuj na matowym papierze.
- **Liczba uczniów:** słownik `DICT_4X4_250` = do 250 ID. Więcej — zmień
  `DICT_NAME` w `aruco_common.py` (np. `DICT_5X5_1000`) i wygeneruj karty od nowa.
- **Stabilność odczytu:** odpowiedź jest potwierdzana po kilku zgodnych
  klatkach, więc obracanie karty nie „miga". Parametr w `camera_worker.py`
  (`stable_frames`).
- **AprilTag** (jeszcze większy zasięg): podmień słownik na
  `DICT_APRILTAG_36h11` w `aruco_common.py`.

## Format quizu (JSON w `quizzes/`)

```json
{
  "title": "Nazwa quizu",
  "questions": [
    {
      "text": "Treść pytania?",
      "answers": ["A", "B", "C", "D"],
      "correct": 1,
      "time": 20,
      "points": 1000
    }
  ]
}
```

`correct` to indeks 0–3 (0=A, 1=B, 2=C, 3=D). Edytor zapisuje ten format
automatycznie — ręczna edycja nie jest potrzebna.

## Integracja we własnym kodzie

Silnik detekcji jest niezależny — możesz go użyć bez całej aplikacji:

```python
from scanner import QuizScanEngine
import cv2

engine = QuizScanEngine(stable_frames=6)
cap = cv2.VideoCapture(0)
ok, frame = cap.read()
detections = engine.process(frame)   # [(id, 'A'/'B'/'C'/'D', rogi), ...]
answers = engine.snapshot()          # {id_ucznia: 'A'/'B'/'C'/'D'}
```

## Dlaczego ArUco, a nie kody QR

Kody QR są większe i gorzej czytają się z daleka oraz pod kątem, a jeden kadr
z wieloma kodami bywa zawodny. Markery ArUco/AprilTag zaprojektowano właśnie
do wykrywania **wielu znaczników jednocześnie** z pomiarem obrotu — to
dokładnie mechanizm, na którym opiera się Plickers.

