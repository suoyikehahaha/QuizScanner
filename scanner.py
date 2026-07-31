"""
Skaner odpowiedzi z kamery (odpowiednik silnika Plickers).

Odczytuje na zywo markery ArUco z kamery, ustala odpowiedz A/B/C/D
kazdego ucznia (na podstawie obrotu karty) i zbiera wyniki.

Klasa QuizScanEngine jest niezalezna od interfejsu -- mozesz ja
zaimportowac do swojej aplikacji z quizami i podawac klatki z dowolnego
zrodla. Funkcja main() to gotowe demo z podgladem z kamery.

Uzycie:
  python scanner.py
  python scanner.py --camera 1 --names students.csv --stable 6

Klawisze w oknie podgladu:
  q  -- wyjscie
  s  -- zapis biezacych (potwierdzonych) odpowiedzi do CSV
  c  -- wyczysc wyniki (nowe pytanie)
  m  -- lustro obrazu wl/wyl
"""

import argparse
import csv
import datetime as dt
from collections import deque, Counter

import cv2
import numpy as np

from aruco_common import make_detector, answer_from_corners


# Kolory (BGR) dla poszczegolnych odpowiedzi -- czytelny overlay.
ANSWER_COLORS = {
    "A": (60, 180, 75),    # zielony
    "B": (230, 160, 40),   # niebieski
    "C": (40, 120, 240),   # pomaranczowy
    "D": (200, 70, 200),   # fioletowy
}


class QuizScanEngine:
    """Wykrywa markery i utrzymuje POTWIERDZONE odpowiedzi.

    Odpowiedz jest potwierdzana dopiero, gdy przez `stable_frames`
    kolejnych klatek marker daje ten sam wynik -- eliminuje migotanie
    przy obracaniu karty.
    """

    def __init__(self, stable_frames=6):
        self.detector = make_detector()
        self.stable_frames = stable_frames
        self._history = {}   # id -> deque ostatnich odczytow
        self.stable = {}     # id -> potwierdzona odpowiedz

    def process(self, frame_bgr):
        """Przetwarza jedna klatke. Zwraca liste (id, odpowiedz, rogi)."""
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        detections = []
        if ids is not None:
            for c, i in zip(corners, ids.flatten()):
                ans = answer_from_corners(c)
                detections.append((int(i), ans, c.reshape(4, 2)))
                self._update(int(i), ans)
        return detections

    def _update(self, mid, ans):
        dq = self._history.setdefault(mid, deque(maxlen=self.stable_frames))
        dq.append(ans)
        # Potwierdz, gdy caly bufor jest zgodny.
        if len(dq) == self.stable_frames and len(set(dq)) == 1:
            self.stable[mid] = ans

    def snapshot(self):
        """Kopia potwierdzonych odpowiedzi: {id: 'A'/'B'/'C'/'D'}."""
        return dict(self.stable)

    def reset(self):
        self._history.clear()
        self.stable.clear()


def draw_detection(frame, mid, ans, corners, name=None):
    """Rysuje obwiednie markera, ID, odpowiedz i wskaznik krawedzi 'do gory'."""
    color = ANSWER_COLORS.get(ans, (0, 0, 0))
    pts = corners.astype(np.int32)
    cv2.polylines(frame, [pts], True, color, 3)

    cx, cy = int(corners[:, 0].mean()), int(corners[:, 1].mean())

    # Duza litera odpowiedzi w srodku markera.
    cv2.putText(frame, ans, (cx - 18, cy + 16), cv2.FONT_HERSHEY_SIMPLEX,
                1.4, color, 4, cv2.LINE_AA)

    # Etykieta ID / imie nad markerem.
    label = f"#{mid}" + (f" {name}" if name else "")
    top = pts[corners[:, 1].argmin()]
    cv2.putText(frame, label, (top[0] - 10, top[1] - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 3, cv2.LINE_AA)
    cv2.putText(frame, label, (top[0] - 10, top[1] - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1, cv2.LINE_AA)


def draw_panel(frame, engine, live_answers, names):
    """Rysuje panel wynikow: potwierdzeni uczniowie + rozklad odpowiedzi."""
    stable = engine.snapshot()
    h, w = frame.shape[:2]
    pw = 250
    panel = frame[:, w - pw:].copy()
    panel = cv2.addWeighted(panel, 0.35,
                            np.zeros_like(panel), 0.0, 40)
    frame[:, w - pw:] = panel
    x0 = w - pw + 14

    cv2.putText(frame, f"Potwierdzeni: {len(stable)}", (x0, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

    # Rozklad odpowiedzi.
    dist = Counter(stable.values())
    bx = x0
    for lab in ("A", "B", "C", "D"):
        col = ANSWER_COLORS[lab]
        cv2.putText(frame, f"{lab}:{dist.get(lab, 0)}", (bx, 62),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2, cv2.LINE_AA)
        bx += 62

    # Lista uczniow (do wysokosci panelu).
    y = 92
    for mid in sorted(stable):
        col = ANSWER_COLORS.get(stable[mid], (200, 200, 200))
        who = names.get(mid, f"#{mid}")
        cv2.putText(frame, f"{who} = {stable[mid]}", (x0, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 1, cv2.LINE_AA)
        y += 22
        if y > h - 40:
            cv2.putText(frame, "...", (x0, y), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (200, 200, 200), 1, cv2.LINE_AA)
            break

    # Podpowiedz klawiszy.
    cv2.putText(frame, "s:zapis  c:reset  m:lustro  q:wyjscie",
                (12, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (255, 255, 255), 1, cv2.LINE_AA)


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
        wr.writerow(["id", "imie", "odpowiedz"])
        for mid, ans in sorted(engine.snapshot().items()):
            wr.writerow([mid, names.get(mid, ""), ans])
    print(f"Zapisano wyniki: {path}  ({len(engine.snapshot())} odpowiedzi)")
    return path


def main():
    ap = argparse.ArgumentParser(description="Skaner odpowiedzi ArUco.")
    ap.add_argument("--camera", type=int, default=0, help="Indeks kamery.")
    ap.add_argument("--names", type=str, default=None, help="CSV: id,imie.")
    ap.add_argument("--stable", type=int, default=6,
                    help="Ile zgodnych klatek potwierdza odpowiedz.")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    args = ap.parse_args()

    names = load_names(args.names) if args.names else {}
    engine = QuizScanEngine(stable_frames=args.stable)

    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    if not cap.isOpened():
        print(f"Nie moge otworzyc kamery {args.camera}.")
        return

    mirror = True
    print("Skaner uruchomiony. Klawisze: s=zapis, c=reset, m=lustro, q=wyjscie.")
    win = "Skaner odpowiedzi (ArUco)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if mirror:
            frame = cv2.flip(frame, 1)

        detections = engine.process(frame)
        live = {}
        for mid, ans, corners in detections:
            live[mid] = ans
            draw_detection(frame, mid, ans, corners, names.get(mid))

        draw_panel(frame, engine, live, names)
        cv2.imshow(win, frame)

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
