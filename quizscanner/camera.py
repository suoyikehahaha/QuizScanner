"""
Wątek kamery: ciągły odczyt markerów ArUco i zasilanie sesji quizu.

Zawsze produkuje adnotowaną klatkę JPEG (podgląd w panelu nauczyciela),
a w fazie 'question' zapisuje potwierdzone odpowiedzi do QuizSession.
"""

import sys
import threading
import time

import cv2
import numpy as np

from .overlay import TextBatch
from .scanner import QuizScanEngine, draw_detection
from .session import PHASE_QUESTION


def _placeholder(text, w=960, h=540):
    """Klatka zastępcza, gdy nie ma obrazu (napis przez PIL — polskie znaki)."""
    img = np.full((h, w, 3), 40, np.uint8)
    batch = TextBatch()
    batch.add(text, (40, h // 2 - 20), size=30, color=(200, 200, 200))
    batch.flush(img)
    return img


class CameraScanner(threading.Thread):
    def __init__(self, session, camera=0, width=1280, height=720,
                 stable_frames=5, mirror=True, only_known=True):
        super().__init__(daemon=True)
        self.session = session
        self.camera = camera          # numer kamery albo adres strumienia
        self.width = width
        self.height = height
        self.mirror = mirror
        self.only_known = only_known
        self.engine = QuizScanEngine(stable_frames=stable_frames)
        self._jpeg = None
        self._lock = threading.Lock()
        self._running = True
        self._last_phase = None
        self.camera_ok = False
        self.live_count = 0
        self.rejected = 0             # ile wykryć odrzucono jako nie-karty

    def _open(self):
        """Otwiera źródło obrazu: kamerę lokalną albo strumień z telefonu."""
        src = self.camera
        if isinstance(src, str):
            src = src.strip()
            if src.isdigit():
                src = int(src)
        if isinstance(src, int):
            # Na Windows DirectShow otwiera kamerę znacznie szybciej niż MSMF.
            backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
            cap = cv2.VideoCapture(src, backend)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        else:
            # Adres sieciowy (telefon z aplikacją IP Webcam / DroidCam itp.).
            cap = cv2.VideoCapture(src)
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # mniejsze opóźnienie
        except Exception:
            pass
        return cap

    def run(self):
        cap = self._open()
        if not cap.isOpened():
            self._store(_placeholder(f"Brak obrazu ze źródła: {self.camera}"))

        while self._running:
            ok, frame = cap.read()
            if not ok:
                self.camera_ok = False
                self._store(_placeholder("Brak sygnału z kamery"))
                time.sleep(0.1)
                continue
            self.camera_ok = True  # potwierdzenie po pierwszej udanej klatce

            phase = self.session.phase
            # Reset silnika na starcie każdego nowego pytania.
            if phase == PHASE_QUESTION and self._last_phase != PHASE_QUESTION:
                self.engine.reset()
            self._last_phase = phase

            # WAŻNE: detekcja zawsze na ORYGINALNEJ klatce. Markery ArUco nie są
            # symetryczne -- w odbiciu lustrzanym ich wzór nie pasuje do słownika
            # i większość kart nie zostałaby wykryta. Lustro służy wyłącznie
            # wygodzie patrzenia i jest nakładane dopiero na podgląd.
            # Filtr ID: gdy włączone, akceptujemy tylko numery z listy uczniów.
            roster = self.session.roster
            self.engine.allowed_ids = (set(roster) if (self.only_known and roster)
                                       else None)

            detections = self.engine.process(frame)
            self.live_count = len(detections)

            if phase == PHASE_QUESTION:
                self.session.record_answers(self.engine.snapshot())

            # Podgląd: opcjonalne lustro + przeliczenie współrzędnych rogów,
            # żeby ramki trafiały w karty, a podpisy pozostały czytelne.
            if self.mirror:
                view = cv2.flip(frame, 1)
                w = view.shape[1]
                detections = [(mid, ans, self._mirror_corners(corners, w))
                              for mid, ans, corners in detections]
            else:
                view = frame

            # Napisy (w tym imiona z polskimi znakami) rysujemy jednym
            # przejściem przez PIL -- OpenCV nie obsługuje takich znaków.
            names = self.session.roster
            batch = TextBatch()
            for mid, ans, corners in detections:
                draw_detection(view, mid, ans, corners, names.get(mid), batch=batch)

            self._banner(view, phase, batch)
            batch.flush(view)
            self._store(view)

        cap.release()

    @staticmethod
    def _mirror_corners(corners, width):
        """Przenosi rogi markera na obraz odbity w poziomie (x -> W-1-x)."""
        pts = np.array(corners, dtype=np.float32).reshape(4, 2).copy()
        pts[:, 0] = (width - 1) - pts[:, 0]
        return pts

    def _banner(self, frame, phase, batch):
        label = {
            PHASE_QUESTION: "ZBIERANIE ODPOWIEDZI",
        }.get(phase, "PODGLĄD")
        color = (60, 200, 90) if phase == PHASE_QUESTION else (180, 180, 180)
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 38), (25, 25, 25), -1)
        batch.add(f"{label}   |   wykryto kart: {self.live_count}",
                  (12, 8), size=22, color=color)

    def _store(self, frame):
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 72])
        if ok:
            with self._lock:
                self._jpeg = buf.tobytes()

    def get_jpeg(self):
        with self._lock:
            return self._jpeg

    def stop(self):
        self._running = False
