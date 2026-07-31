"""
Generator kart do druku (odpowiednik kart Plickers).

Kazda karta zawiera:
  - jeden marker ArUco o unikalnym ID (= uczen),
  - litery A / B / C / D przy czterech krawedziach, obrocone tak, aby
    kazda byla czytelna, gdy jej krawedz jest u gory,
  - naglowek z numerem ID i (opcjonalnie) imieniem ucznia.

Uzycie:
  python generate_cards.py --count 30
  python generate_cards.py --names students.csv
  python generate_cards.py --count 30 --out karty --card-mm 148 210

Wynik:
  - PNG kazdej karty w folderze wyjsciowym (do druku 1 na strone),
  - zbiorczy plik karty.pdf (jedna karta na strone A4) jesli jest Pillow.
"""

import argparse
import csv
import os

import cv2
import numpy as np

from aruco_common import get_dictionary, ANSWER_LABELS


def render_text(text, font_scale, thickness, color=(0, 0, 0)):
    """Rysuje tekst na wlasnym bialym kafelku i go zwraca (BGR)."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    (w, h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    pad = thickness * 2 + 6
    tile = np.full((h + baseline + pad * 2, w + pad * 2, 3), 255, np.uint8)
    cv2.putText(tile, text, (pad, h + pad), font, font_scale, color,
                thickness, cv2.LINE_AA)
    return tile


def rotate90(img, angle):
    """Obrot o wielokrotnosc 90 stopni. Dodatni = przeciwnie do zegara."""
    angle %= 360
    if angle == 0:
        return img
    if angle == 90:
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if angle == 180:
        return cv2.rotate(img, cv2.ROTATE_180)
    if angle == 270:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    raise ValueError("Obslugiwane sa tylko katy 0/90/180/270.")


def paste_center(dst, patch, cx, cy):
    """Wkleja kafelek 'patch' na 'dst' tak, aby jego srodek byl w (cx, cy)."""
    ph, pw = patch.shape[:2]
    x0 = int(round(cx - pw / 2))
    y0 = int(round(cy - ph / 2))
    x1, y1 = x0 + pw, y0 + ph
    # Przyciecie do granic plotna (bezpiecznik).
    x0c, y0c = max(0, x0), max(0, y0)
    x1c, y1c = min(dst.shape[1], x1), min(dst.shape[0], y1)
    if x1c <= x0c or y1c <= y0c:
        return
    dst[y0c:y1c, x0c:x1c] = patch[y0c - y0:y1c - y0, x0c - x0:x1c - x0]


def make_card(marker_id, name, dictionary, size_px, marker_px):
    """Buduje pojedyncza karte (obraz BGR)."""
    W, H = size_px
    card = np.full((H, W, 3), 255, np.uint8)
    cv2.rectangle(card, (10, 10), (W - 10, H - 10), (0, 0, 0), 3)

    cx, cy = W // 2, H // 2

    # Marker w srodku.
    marker = cv2.aruco.generateImageMarker(dictionary, marker_id, marker_px)
    marker = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
    paste_center(card, marker, cx, cy)

    # Litery przy krawedziach. Kazda obrocona tak, by byla czytelna,
    # gdy jej krawedz jest u gory (A gora, B prawo, C dol, D lewo).
    offset = marker_px // 2 + int(marker_px * 0.16)
    letter_scale = marker_px / 190.0
    letter_th = max(3, marker_px // 70)
    placements = {
        "A": (cx, cy - offset, 0),
        "B": (cx + offset, cy, 270),
        "C": (cx, cy + offset, 180),
        "D": (cx - offset, cy, 90),
    }
    for letter, (px, py, ang) in placements.items():
        tile = render_text(letter, letter_scale, letter_th)
        tile = rotate90(tile, ang)
        paste_center(card, tile, px, py)

    # Naglowek: ID + imie.
    header = f"#{marker_id}"
    if name:
        header += f"   {name}"
    cv2.putText(card, header, (28, 62), cv2.FONT_HERSHEY_SIMPLEX,
                W / 720.0, (0, 0, 0), 2, cv2.LINE_AA)

    # Stopka z instrukcja.
    cv2.putText(card, "Obroc wybrana litere do gory i podnies karte",
                (28, H - 26), cv2.FONT_HERSHEY_SIMPLEX,
                W / 1150.0, (90, 90, 90), 2, cv2.LINE_AA)
    return card


def load_names(path):
    """Wczytuje pary (id, imie) z pliku CSV. Naglowek opcjonalny.

    Akceptowane formaty wiersza:
      id,imie
      imie              (ID nadawane kolejno od 0)
    """
    names = {}
    order = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row or not row[0].strip():
                continue
            first = row[0].strip()
            if first.lower() in ("id", "#", "numer"):
                continue  # naglowek
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
                    help="Liczba kart o ID 0..count-1 (jesli nie podano --names).")
    ap.add_argument("--names", type=str, default=None,
                    help="Plik CSV z imionami (id,imie lub samo imie).")
    ap.add_argument("--out", type=str, default="karty",
                    help="Folder wyjsciowy (domyslnie: karty).")
    ap.add_argument("--card-mm", type=float, nargs=2, default=[148.0, 210.0],
                    metavar=("SZER", "WYS"), help="Rozmiar karty w mm (domyslnie A5).")
    ap.add_argument("--dpi", type=int, default=200, help="Rozdzielczosc druku (DPI).")
    ap.add_argument("--no-pdf", action="store_true", help="Nie skladaj zbiorczego PDF.")
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

    print(f"Zapisano {len(card_paths)} plikow PNG w: {args.out}")

    if not args.no_pdf:
        try:
            from PIL import Image
            pages = [Image.open(p).convert("RGB") for p in card_paths]
            pdf_path = os.path.join(args.out, "karty.pdf")
            pages[0].save(pdf_path, save_all=True, append_images=pages[1:],
                          resolution=float(args.dpi))
            print(f"Zapisano zbiorczy PDF: {pdf_path}")
        except ImportError:
            print("Pillow niedostepny -- pomijam PDF (PNG-i sa gotowe do druku).")


if __name__ == "__main__":
    main()
