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
        self._jpeg_condition = threading.Condition(self._lock)
        self._jpeg_sequence = 0
        self._phone_lock = threading.Lock()
        self._phone_condition = threading.Condition(self._phone_lock)
        self._phone_frame = None
        self._phone_display_rotation = 0
        self._phone_frame_at = 0.0
        self._phone_frame_sequence = 0
        self._running = True
        self._last_phase = None
        self._last_question_index = None
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

    def accepts_phone_frames(self):
        """Return whether this scanner is currently configured for the APK camera."""
        return str(self.camera).strip().casefold() == "android"

    def submit_phone_jpeg(self, encoded, image_rotation=0, display_rotation=0):
        """Decode, orient, and retain the newest frame from the Android app."""
        if not self.accepts_phone_frames() or not encoded:
            return False
        frame = cv2.imdecode(np.frombuffer(encoded, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return False
        image_rotation = int(image_rotation) % 360
        if image_rotation == 90:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif image_rotation == 180:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        elif image_rotation == 270:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        display_rotation = int(display_rotation) % 360
        height, width = frame.shape[:2]
        max_width, max_height = (720, 1280) if height > width else (1280, 720)
        scale = min(1.0, max_width / max(1, width), max_height / max(1, height))
        if scale < 1.0:
            frame = cv2.resize(frame, (int(width * scale), int(height * scale)),
                               interpolation=cv2.INTER_AREA)
        with self._phone_condition:
            self._phone_frame = frame
            self._phone_display_rotation = display_rotation
            self._phone_frame_at = time.monotonic()
            self._phone_frame_sequence += 1
            self._phone_condition.notify_all()
        return True

    def _next_phone_frame(self, last_sequence, timeout=0.25):
        """Wait for a new phone frame; never redetect a stale image in a tight loop."""
        with self._phone_condition:
            if self._phone_frame_sequence <= last_sequence and self._running:
                self._phone_condition.wait_for(
                    lambda: self._phone_frame_sequence > last_sequence or not self._running,
                    timeout=timeout,
                )
            sequence = self._phone_frame_sequence
            if sequence > last_sequence and self._phone_frame is not None:
                return self._phone_frame, sequence, False, self._phone_display_rotation
            stale = (self._phone_frame is None
                     or time.monotonic() - self._phone_frame_at > 2.0)
            return None, last_sequence, stale, self._phone_display_rotation

    def run(self):
        phone_source = self.accepts_phone_frames()
        phone_sequence = 0
        cap = None if phone_source else self._open()
        if phone_source:
            self._store(_placeholder("等待手机摄像头画面"))
        if cap is not None and not cap.isOpened():
            self._store(_placeholder(f"Brak obrazu ze źródła: {self.camera}"))

        while self._running:
            if phone_source:
                frame, phone_sequence, stale, phone_display_rotation = self._next_phone_frame(phone_sequence)
                ok = frame is not None
                if not ok:
                    if stale and self.camera_ok:
                        self.camera_ok = False
                        self.live_count = 0
                        self._store(_placeholder("手机摄像头连接已中断"))
                    continue
            else:
                ok, frame = cap.read()
                phone_display_rotation = 0
            if not ok:
                self.camera_ok = False
                self.live_count = 0
                message = "Oczekiwanie na kamerę telefonu" if phone_source else "Brak sygnału z kamery"
                self._store(_placeholder(message))
                time.sleep(0.1)
                continue
            self.camera_ok = True  # potwierdzenie po pierwszej udanej klatce

            phase = self.session.phase
            question_index = getattr(self.session, "attempt_id", None)
            new_question = (phase == PHASE_QUESTION
                            and (self._last_phase != PHASE_QUESTION
                                 or question_index != self._last_question_index))
            # Android rotates each uploaded frame into the current screen
            # orientation before sending it. Read the edge at the top of that
            # visible frame, regardless of whether the phone is portrait or
            # landscape; a question-start rotation anchor can invert that edge.
            if new_question:
                self.engine.reset()
            self._last_phase = phase
            self._last_question_index = question_index

            # WAŻNE: detekcja zawsze na ORYGINALNEJ klatce. Markery ArUco nie są
            # symetryczne -- w odbiciu lustrzanym ich wzór nie pasuje do słownika
            # i większość kart nie zostałaby wykryta. Lustro służy wyłącznie
            # wygodzie patrzenia i jest nakładane dopiero na podgląd.
            # Filtr ID: gdy włączone, akceptujemy tylko numery z listy uczniów.
            roster = self.session.roster
            self.engine.allowed_ids = (set(roster) if self.only_known
                                       else None)

            if phone_source:
                phone_up_vector = (0.0, -1.0)
            else:
                phone_up_vector = None
            detections = self.engine.process(frame, up_vector=phone_up_vector)
            self.live_count = len(detections)

            if phase == PHASE_QUESTION and self.session.input_source != "native":
                self.session.record_answers(self.engine.snapshot(), attempt_id=question_index)

            # Podgląd: opcjonalne lustro + przeliczenie współrzędnych rogów,
            # żeby ramki trafiały w karty, a podpisy pozostały czytelne.
            # 手机后置摄像头预览必须保持正向；镜像只用于电脑本机摄像头的自拍式预览。
            mirror_preview = self.mirror and not phone_source
            if mirror_preview:
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
                student = names.get(mid) or {}
                label = " ".join(part for part in (
                    str(student.get("student_no", "")),
                    str(student.get("name", "")),
                ) if part)
                draw_detection(view, mid, ans, corners, label, batch=batch)

            self._banner(view, phase, batch)
            batch.flush(view)
            self._store(view)

        if cap is not None:
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
        quality = 62 if self.accepts_phone_frames() else 72
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if ok:
            with self._jpeg_condition:
                self._jpeg = buf.tobytes()
                self._jpeg_sequence += 1
                self._jpeg_condition.notify_all()

    def get_jpeg(self):
        with self._lock:
            return self._jpeg

    def get_jpeg_after(self, sequence, timeout=0.5):
        """Block until a newer preview frame exists instead of streaming duplicates."""
        with self._jpeg_condition:
            if self._jpeg_sequence <= sequence and self._running:
                self._jpeg_condition.wait_for(
                    lambda: self._jpeg_sequence > sequence or not self._running,
                    timeout=timeout,
                )
            if self._jpeg_sequence > sequence:
                return self._jpeg_sequence, self._jpeg
            return self._jpeg_sequence, None

    def stop(self):
        self._running = False
        with self._phone_condition:
            self._phone_condition.notify_all()
        with self._jpeg_condition:
            self._jpeg_condition.notify_all()
