"""
Rysowanie napisów na klatkach wideo z obsługą polskich znaków.

OpenCV (`cv2.putText`) potrafi narysować wyłącznie znaki ASCII — polskie
litery wychodzą jako znaki zapytania. Dlatego napisy nakładamy przez PIL,
zbierając je najpierw do listy i rysując **jednym przejściem na klatkę**
(konwersja BGR↔PIL jest kosztowna, więc robimy ją raz).

Użycie:

    batch = TextBatch()
    batch.add("Zażółć gęślą jaźń", (10, 20), size=22, color=(255, 255, 255))
    batch.flush(frame)          # dopiero tutaj powstaje obraz z napisami
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw

from generate_cards import get_font


class TextBatch:
    """Zbiera napisy i rysuje je wszystkie naraz na klatce."""

    def __init__(self):
        self.items = []

    def add(self, text, xy, size=20, color=(255, 255, 255), bold=True,
            outline=None):
        """color i outline podajemy w BGR (jak w OpenCV)."""
        if text:
            self.items.append((str(text), xy, int(size), color, bold, outline))

    def flush(self, frame_bgr):
        """Rysuje zebrane napisy na klatce (w miejscu) i czyści listę."""
        if not self.items:
            return frame_bgr
        img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img)
        for text, xy, size, color, bold, outline in self.items:
            font = get_font(size, bold)
            rgb = (color[2], color[1], color[0])
            if outline is not None:
                ol = (outline[2], outline[1], outline[0])
                draw.text(xy, text, font=font, fill=rgb,
                          stroke_width=max(2, size // 10), stroke_fill=ol)
            else:
                draw.text(xy, text, font=font, fill=rgb)
        out = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        frame_bgr[:, :, :] = out
        self.items.clear()
        return frame_bgr


def text_size(text, size=20, bold=True):
    """Szerokość i wysokość napisu w pikselach."""
    font = get_font(size, bold)
    box = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]
