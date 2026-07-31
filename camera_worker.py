"""
Watek kamery: ciagly odczyt markerow ArUco i zasilanie sesji quizu.

Zawsze produkuje adnotowana klatke JPEG (podglad w panelu nauczyciela),
a w fazie 'question' zapisuje potwierdzone odpowiedzi do QuizSession.
"""

import sys
import threading
import time

import cv2
import numpy as np

from scanner import QuizScanEngine, draw_detection
from quiz_session import PHASE_QUESTION


def _placeholder(text, w=960, h=540):
    img = np.full((h, w, 3), 40, np.uint8)
    cv2.putText(img, text, (40, h // 2), cv2.FONT_HERSHEY_SIMPLEX,
                1.0, (200, 200, 200), 2, cv2.LINE_AA)
    return img


class CameraScanner(threading.Thread):
    def __init__(self, session, camera=0, width=1280, height=720,
                 stable_frames=5, mirror=True):
        super().__init__(daemon=True)
        self.session = session
        self.camera = camera
        self.width = width
        self.height = height
        self.mirror = mirror
        self.engine = QuizScanEngine(stable_frames=stable_frames)
        self._jpeg = None
        self._lock = threading.Lock()
        self._running = True
        self._last_phase = None
        self.camera_ok = False
        self.live_count = 0

    def run(self):
        # Na Windows backend DirectShow otwiera kamere znacznie szybciej niz
        # domyslny MSMF (ktory potrafi wisiec kilka sekund).
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        cap = cv2.VideoCapture(self.camera, backend)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        if not cap.isOpened():
            self._store(_placeholder(f"Brak kamery (indeks {self.camera})"))

        while self._running:
            ok, frame = cap.read()
            if not ok:
                self.camera_ok = False
                self._store(_placeholder("Brak sygnalu z kamery"))
                time.sleep(0.1)
                continue
            self.camera_ok = True  # potwierdzenie po pierwszej udanej klatce

            if self.mirror:
                frame = cv2.flip(frame, 1)

            phase = self.session.phase
            # Reset silnika na starcie kazdego nowego pytania.
            if phase == PHASE_QUESTION and self._last_phase != PHASE_QUESTION:
                self.engine.reset()
            self._last_phase = phase

            detections = self.engine.process(frame)
            self.live_count = len(detections)

            if phase == PHASE_QUESTION:
                self.session.record_answers(self.engine.snapshot())

            names = self.session.roster
            for mid, ans, corners in detections:
                draw_detection(frame, mid, ans, corners, names.get(mid))

            self._banner(frame, phase)
            self._store(frame)

        cap.release()

    def _banner(self, frame, phase):
        label = {
            PHASE_QUESTION: "ZBIERANIE ODPOWIEDZI",
        }.get(phase, "PODGLAD")
        color = (60, 200, 90) if phase == PHASE_QUESTION else (180, 180, 180)
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 34), (25, 25, 25), -1)
        cv2.putText(frame, f"{label}  |  wykryto kart: {self.live_count}",
                    (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)

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
