# QuizScanner — darmowy system quizowy z odczytem kart z kamery

Pełna alternatywa dla Plickers: uczniowie odpowiadają, podnosząc wydrukowane
karty z markerami **ArUco**, a kamera odczytuje wszystkie odpowiedzi naraz.
Do tego panel nauczyciela, widok na tablicę/rzutnik (własny motyw „Scan") i
edytor pytań. Całość działa **offline**, na Windows i Linux, bez kont i limitów.

Zbudowane wyłącznie na bibliotece standardowej Pythona + OpenCV / NumPy /
Pillow — **bez Flask i bez żadnych instalacji**, jeśli masz już te trzy pakiety.

## Jak to działa

- Każda karta ma jeden marker ArUco o unikalnym ID = konkretny uczeń.
- Krawędzie karty opisane są literami **A / B / C / D**.
- Uczeń obraca kartę tak, aby wybrana litera była **u góry**.
- Kamera w jednym kadrze wykrywa wielu uczniów, odczytuje ID i obrót → odpowiedź.
- Domyślnie każda poprawna odpowiedź warta jest tyle samo punktów. Punkty za
  szybkość (kto pierwszy, ten więcej) można włączyć przełącznikiem w panelu.
- Jest ranking i podium.

## Szybki start

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
   gotowego `Przykladowy quiz`). W zakładce **Uczniowie** wpisz listę klasy
   (ID = numer na karcie).

3. **Wydrukuj karty**:

   ```bash
   python generate_cards.py --names students.csv --out karty
   ```

   Powstaną pliki PNG i zbiorczy `karty/karty.pdf` (jedna karta na stronę A4).

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
| `students.csv` | lista uczniów (id,imie) do druku kart |

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
