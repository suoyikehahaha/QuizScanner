"""
Skaner odpowiedzi z kamery (odpowiednik silnika Plickers).

Odczytuje na zywo markery ArUco z kamery, ustala odpowiedź A/B/C/D
każdego ucznia (na podstawie obrotu karty) i zbiera wyniki.

Klasa QuizScanEngine jest niezależna od interfejsu -- możesz ja
zaimportować do swojej aplikacji z quizami i podawać klatki z dowolnego
źródła. Funkcja main() to gotowe demo z podglądem z kamery.

Użycie:
  python scanner.py
  python scanner.py --camera 1 --names students.csv --stable 6

Klawisze w oknie podglądu:
  q  -- wyjście
  s  -- zapis bieżących (potwierdzonych) odpowiedzi do CSV
  c  -- wyczyść wyniki (nowe pytanie)
  m  -- lustro obrazu wl/wyl
"""

import argparse
import csv
import datetime as dt
from collections import deque, Counter

import cv2
import numpy as np

from .aruco import (make_detector, answer_from_corners,
                          marker_is_black_and_white)
from .overlay import TextBatch


# Kolory (BGR) dla poszczególnych odpowiedzi -- czytelny overlay.
ANSWER_COLORS = {
    "A": (60, 180, 75),    # zielony
    "B": (230, 160, 40),   # niebieski
    "C": (40, 120, 240),   # pomarańczowy
    "D": (200, 70, 200),   # fioletowy
}


class QuizScanEngine:
    """Wykrywa markery i utrzymuje POTWIERDZONE odpowiedzi.

    Odpowiedź jest potwierdzana dopiero, gdy przez `stable_frames`
    kolejnych klatek marker daje ten sam wynik -- eliminuje migotanie
    przy obracaniu karty.
    """

    def __init__(self, stable_frames=6, allowed_ids=None, strict=True):
        self.detector = make_detector(strict=strict)
        self.stable_frames = stable_frames
        self.allowed_ids = set(allowed_ids) if allowed_ids else None
        self.check_contrast = strict
        self._history = {}   # id -> deque ostatnich odczytów
        self.stable = {}     # id -> potwierdzona odpowiedź

    def process(self, frame_bgr, up_vector=None):
        """Przetwarza jedna klatkę. Zwraca listę (id, odpowiedź, rogi).

        Odrzuca wykrycia, które nie wyglądają na wydrukowana kartę:
        spoza dozwolonej listy ID albo bez wyraźnego czarno-białego wzoru.
        """
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        detections = []
        if ids is not None:
            for c, i in zip(corners, ids.flatten()):
                mid = int(i)
                if self.allowed_ids is not None and mid not in self.allowed_ids:
                    continue
                if self.check_contrast and not marker_is_black_and_white(gray, c):
                    continue
                ans = answer_from_corners(c, up_vector=up_vector)
                detections.append((mid, ans, c.reshape(4, 2)))
                self._update(mid, ans)
        return detections

    def _update(self, mid, ans):
        dq = self._history.setdefault(mid, deque(maxlen=self.stable_frames))
        dq.append(ans)
        # Potwierdź, gdy cały bufor jest zgodny.
        if len(dq) == self.stable_frames and len(set(dq)) == 1:
            self.stable[mid] = ans

    def snapshot(self):
        """Kopia potwierdzonych odpowiedzi: {id: 'A'/'B'/'C'/'D'}."""
        return dict(self.stable)

    def reset(self):
        self._history.clear()
        self.stable.clear()


def mirror_corners(corners, width):
    """Przenosi rogi markera na obraz odbity w poziomie (x -> W-1-x)."""
    pts = np.array(corners, dtype=np.float32).reshape(4, 2).copy()
    pts[:, 0] = (width - 1) - pts[:, 0]
    return pts


def draw_detection(frame, mid, ans, corners, name=None, batch=None):
    """Rysuje obwiednię markera, ID, odpowiedź i wskaźnik krawędzi 'do góry'.

    Napisy trafiają do `batch` (TextBatch), bo imiona uczniów zawierają
    polskie znaki, których OpenCV nie potrafi narysować. Gdy batch nie jest
    podany, napisy rysowane są od razu (wolniej, ale wygodnie w testach).
    """
    own_batch = batch is None
    if own_batch:
        batch = TextBatch()

    color = ANSWER_COLORS.get(ans, (0, 0, 0))
    pts = corners.astype(np.int32)
    cv2.polylines(frame, [pts], True, color, 3)

    cx, cy = int(corners[:, 0].mean()), int(corners[:, 1].mean())

    # Duża litera odpowiedzi w środku markera.
    batch.add(ans, (cx - 16, cy - 26), size=46, color=color,
              bold=True, outline=(20, 20, 20))

    # Etykieta ID / imię nad markerem.
    label = f"#{mid}" + (f" {name}" if name else "")
    top = pts[corners[:, 1].argmin()]
    batch.add(label, (int(top[0]) - 10, int(top[1]) - 30), size=20,
              color=color, bold=True, outline=(255, 255, 255))

    if own_batch:
        batch.flush(frame)


def draw_panel(frame, engine, live_answers, names):
    """Rysuje panel wyników: potwierdzeni uczniowie + rozkład odpowiedzi."""
    stable = engine.snapshot()
    h, w = frame.shape[:2]
    pw = 250
    panel = frame[:, w - pw:].copy()
    panel = cv2.addWeighted(panel, 0.35,
                            np.zeros_like(panel), 0.0, 40)
    frame[:, w - pw:] = panel
    x0 = w - pw + 14
    batch = TextBatch()

    batch.add(f"Potwierdzeni: {len(stable)}", (x0, 18), size=22,
              color=(255, 255, 255))

    # Rozkład odpowiedzi.
    dist = Counter(stable.values())
    bx = x0
    for lab in ("A", "B", "C", "D"):
        col = ANSWER_COLORS[lab]
        batch.add(f"{lab}:{dist.get(lab, 0)}", (bx, 48), size=19, color=col)
        bx += 62

    # Lista uczniów (do wysokości panelu).
    y = 78
    for mid in sorted(stable):
        col = ANSWER_COLORS.get(stable[mid], (200, 200, 200))
        who = names.get(mid, f"#{mid}")
        batch.add(f"{who} = {stable[mid]}", (x0, y), size=17, color=col, bold=False)
        y += 22
        if y > h - 40:
            batch.add("...", (x0, y), size=17, color=(200, 200, 200))
            break

    # Podpowiedź klawiszy.
    batch.add("s:zapis   c:reset   m:lustro   q:wyjście", (12, h - 26),
              size=16, color=(255, 255, 255), bold=False)
    batch.flush(frame)


def load_names(path):
    names = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[0].strip().isdigit():
                names[int(row[0])] = row[1].strip()
    return names


def save_results(engine, names):
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"wyniki_{stamp}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["id", "imię", "odpowiedź"])
        for mid, ans in sorted(engine.snapshot().items()):
            wr.writerow([mid, names.get(mid, ""), ans])
    print(f"Zapisano wyniki: {path}  ({len(engine.snapshot())} odpowiedzi)")
    return path


def main():
    ap = argparse.ArgumentParser(description="Skaner odpowiedzi ArUco.")
    ap.add_argument("--camera", type=int, default=0, help="Indeks kamery.")
    ap.add_argument("--names", type=str, default=None, help="CSV: id,imię.")
    ap.add_argument("--stable", type=int, default=6,
                    help="Ile zgodnych klatek potwierdza odpowiedź.")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    args = ap.parse_args()

    names = load_names(args.names) if args.names else {}
    engine = QuizScanEngine(stable_frames=args.stable)

    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    if not cap.isOpened():
        print(f"Nie mogę otworzyć kamery {args.camera}.")
        return

    mirror = True
    print("Skaner uruchomiony. Klawisze: s=zapis, c=reset, m=lustro, q=wyjście.")
    win = "Skaner odpowiedzi (ArUco)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        # Detekcja zawsze na oryginale -- odbity marker ArUco nie pasuje do
        # słownika i nie zostałby wykryty. Lustro dotyczy tylko podglądu.
        detections = engine.process(frame)
        live = {mid: ans for mid, ans, _ in detections}

        if mirror:
            view = cv2.flip(frame, 1)
            w = view.shape[1]
            detections = [(mid, ans, mirror_corners(corners, w))
                          for mid, ans, corners in detections]
        else:
            view = frame

        for mid, ans, corners in detections:
            draw_detection(view, mid, ans, corners, names.get(mid))

        draw_panel(view, engine, live, names)
        cv2.imshow(win, view)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("s"):
            save_results(engine, names)
        elif key == ord("c"):
            engine.reset()
            print("Wyniki wyczyszczone -- nowe pytanie.")
        elif key == ord("m"):
            mirror = not mirror

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
