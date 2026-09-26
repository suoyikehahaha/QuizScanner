"""
Generator kart do druku (odpowiednik kart Plickers).

Każda karta zawiera:
  - jeden marker ArUco o unikalnym ID (= uczeń),
  - litery A / B / C / D przy czterech krawędziach, obrócone tak, aby
    każda była czytelna, gdy jej krawędź jest u góry,
  - nagłówek z numerem ID i (opcjonalnie) imieniem ucznia.

Użycie:
  python -m quizscanner.cards --count 30
  python -m quizscanner.cards --names data/students.csv
  python -m quizscanner.cards --count 30 --out karty --card-mm 148 210

Wynik:
  - PNG każdej karty w folderze wyjściowym (do druku 1 na stronę),
  - zbiorczy plik karty.pdf (jedna karta na stronę A4) jeśli jest Pillow.
"""

import argparse
import csv
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .aruco import get_dictionary, ANSWER_LABELS
from .i18n import t


# Czcionki TrueType -- potrzebne, bo cv2.putText nie potrafi narysować
# polskich znaków (obsługuje tylko ASCII). Szukamy typowych czcionek
# systemowych; kolejność: Windows, Linux, macOS.
_FONT_CANDIDATES = {
    False: [  # zwykła
        r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/Library/Fonts/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc",
    ],
    True: [   # pogrubiona
        r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc",
    ],
}
_font_cache = {}


def get_font(size, bold=False):
    """Zwraca czcionkę TrueType o zadanym rozmiarze (z pamięcią podręczną)."""
    key = (int(size), bool(bold))
    if key in _font_cache:
        return _font_cache[key]
    font = None
    for path in _FONT_CANDIDATES[bool(bold)]:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, int(size))
                break
            except Exception:
                continue
    if font is None:                      # ostateczność: wbudowana bitmapowa
        font = ImageFont.load_default()
    _font_cache[key] = font
    return font


def render_text(text, size, bold=True, color=(0, 0, 0)):
    """Rysuje tekst na własnym białym kafelku (BGR) -- z polskimi znakami."""
    font = get_font(size, bold)
    dummy = Image.new("RGB", (1, 1), "white")
    box = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
    pad = max(4, int(size * 0.12))
    w = (box[2] - box[0]) + pad * 2
    h = (box[3] - box[1]) + pad * 2
    tile = Image.new("RGB", (max(w, 1), max(h, 1)), "white")
    ImageDraw.Draw(tile).text((pad - box[0], pad - box[1]), text,
                              font=font, fill=color)
    return cv2.cvtColor(np.array(tile), cv2.COLOR_RGB2BGR)


def draw_text(card_bgr, text, xy, size, bold=False, color=(0, 0, 0)):
    """Rysuje tekst bezpośrednio na obrazie BGR (obsługuje UTF-8)."""
    img = Image.fromarray(cv2.cvtColor(card_bgr, cv2.COLOR_BGR2RGB))
    ImageDraw.Draw(img).text(xy, text, font=get_font(size, bold), fill=color)
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def rotate90(img, angle):
    """Obrót o wielokrotność 90 stopni. Dodatni = przeciwnie do zegara."""
    angle %= 360
    if angle == 0:
        return img
    if angle == 90:
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if angle == 180:
        return cv2.rotate(img, cv2.ROTATE_180)
    if angle == 270:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    raise ValueError("Obsługiwane są tylko kąty 0/90/180/270.")


def paste_center(dst, patch, cx, cy):
    """Wkleja kafelek 'patch' na 'dst' tak, aby jego środek był w (cx, cy)."""
    ph, pw = patch.shape[:2]
    x0 = int(round(cx - pw / 2))
    y0 = int(round(cy - ph / 2))
    x1, y1 = x0 + pw, y0 + ph
    # Przycięcie do granic płótna (bezpiecznik).
    x0c, y0c = max(0, x0), max(0, y0)
    x1c, y1c = min(dst.shape[1], x1), min(dst.shape[0], y1)
    if x1c <= x0c or y1c <= y0c:
        return
    dst[y0c:y1c, x0c:x1c] = patch[y0c - y0:y1c - y0, x0c - x0:x1c - x0]


def make_card(marker_id, name, dictionary, size_px, marker_px, lang="zh",
              student_no=None, class_name=None):
    """Buduje pojedynczą kartę (obraz BGR)."""
    W, H = size_px
    card = np.full((H, W, 3), 255, np.uint8)
    cv2.rectangle(card, (10, 10), (W - 10, H - 10), (0, 0, 0), 3)

    cx, cy = W // 2, H // 2

    # Marker w środku.
    marker = cv2.aruco.generateImageMarker(dictionary, marker_id, marker_px)
    marker = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
    paste_center(card, marker, cx, cy)

    # Litery przy krawędziach. Każda obrócona tak, by była czytelna,
    # gdy jej krawędź jest u góry (A góra, B prawo, C dół, D lewo).
    offset = marker_px // 2 + int(marker_px * 0.17)
    placements = {
        "A": (cx, cy - offset, 0),
        "B": (cx + offset, cy, 270),
        "C": (cx, cy + offset, 180),
        "D": (cx - offset, cy, 90),
    }
    for letter, (px, py, ang) in placements.items():
        tile = render_text(letter, int(marker_px * 0.20), bold=True)
        tile = rotate90(tile, ang)
        paste_center(card, tile, px, py)

    # 学号是教师和学生使用的身份标识；ArUco 编号只作为班级内部识别码。
    header = f"学号 {student_no}" if student_no not in (None, "") else f"#{marker_id}"
    if class_name and class_name != "未分班":
        header = f"{class_name}  {header}"
    if name:
        header += f"   {name}"
    card = draw_text(card, header, (30, 26), int(W * 0.048), bold=True)

    # Stopka z instrukcja (w wybranym języku, z polskimi znakami).
    hint = t("card_hint", lang)
    card = draw_text(card, hint, (30, H - int(W * 0.052)),
                     int(W * 0.030), bold=False, color=(105, 105, 105))
    return card


def load_names(path):
    """Wczytuje pary (id, imię) z pliku CSV. Nagłówek opcjonalny.

    Akceptowane formaty wiersza:
      id,imię
      imię              (ID nadawane kolejno od 0)
    """
    names = {}
    order = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row or not row[0].strip():
                continue
            first = row[0].strip()
            if first.lower() in ("id", "#", "numer"):
                continue  # nagłówek
            if len(row) >= 2 and first.isdigit():
                mid = int(first)
                names[mid] = row[1].strip()
                order.append(mid)
            else:
                mid = len(order)
                names[mid] = first
                order.append(mid)
    return order, names


def main():
    ap = argparse.ArgumentParser(description="Generator kart ArUco (styl Plickers).")
    ap.add_argument("--count", type=int, default=None,
                    help="Liczba kart o ID 0..count-1 (jeśli nie podano --names).")
    ap.add_argument("--names", type=str, default=None,
                    help="Plik CSV z imionami (id,imię lub samo imię).")
    ap.add_argument("--out", type=str, default="karty",
                    help="Folder wyjściowy (domyślnie: karty).")
    ap.add_argument("--card-mm", type=float, nargs=2, default=[148.0, 210.0],
                    metavar=("SZER", "WYS"), help="Rozmiar karty w mm (domyślnie A5).")
    ap.add_argument("--dpi", type=int, default=200, help="Rozdzielczość druku (DPI).")
    ap.add_argument("--no-pdf", action="store_true", help="Nie składaj zbiorczego PDF.")
    args = ap.parse_args()

    if args.names:
        order, names = load_names(args.names)
    elif args.count:
        order = list(range(args.count))
        names = {}
    else:
        ap.error("Podaj --count N albo --names plik.csv")

    os.makedirs(args.out, exist_ok=True)
    dictionary = get_dictionary()

    mm_w, mm_h = args.card_mm
    W = int(mm_w / 25.4 * args.dpi)
    H = int(mm_h / 25.4 * args.dpi)
    marker_px = int(min(W, H) * 0.55)

    print(f"Generuje {len(order)} kart  ({W}x{H}px, marker {marker_px}px)...")
    card_paths = []
    for mid in order:
        card = make_card(mid, names.get(mid, ""), dictionary, (W, H), marker_px)
        path = os.path.join(args.out, f"karta_{mid:03d}.png")
        cv2.imwrite(path, card)
        card_paths.append(path)

    print(f"Zapisano {len(card_paths)} plików PNG w: {args.out}")

    if not args.no_pdf:
        try:
            from PIL import Image
            pages = [Image.open(p).convert("RGB") for p in card_paths]
            pdf_path = os.path.join(args.out, "karty.pdf")
            pages[0].save(pdf_path, save_all=True, append_images=pages[1:],
                          resolution=float(args.dpi))
            print(f"Zapisano zbiorczy PDF: {pdf_path}")
        except ImportError:
            print("Pillow niedostępny -- pomijam PDF (PNG-i są gotowe do druku).")


if __name__ == "__main__":
    main()
