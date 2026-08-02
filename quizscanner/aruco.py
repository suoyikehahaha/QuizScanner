"""
Wspólna konfiguracja i logika ArUco dla generatora kart i skanera.

Zasada działania (jak Plickers):
- Każda karta ma jeden marker ArUco o unikalnym ID  =  konkretny uczeń.
- Karta ma 4 krawędzie opisane literami A / B / C / D.
- Uczeń obraca kartę tak, aby wybrana litera była u góry.
- Skaner wykrywa marker, ustala która krawędź jest najwyżej na obrazie
  i odczytuje z tego odpowiedź. Jeden kadr = wiele uczniów naraz.

Ten sam słownik markerów MUSI być użyty w generatorze i w skanerze,
dlatego oba pliki importują stąd DICT_NAME i EDGE_CORNERS.
"""

import cv2
import numpy as np

# Słownik ArUco. 4x4_250 = do 250 unikalnych ID (uczniów),
# małe markery czytelne z dużej odległości. W razie potrzeby zmień tutaj
# w OBU miejscach naraz (generator i skaner używają tej stałej).
DICT_NAME = "DICT_4X4_250"

# Litery odpowiedzi przypisane do krawędzi markera.
# detectMarkers zwraca rogi ZAWSZE w kanonicznej kolejności markera
# (niezależnie od fizycznego obrotu karty), gdzie:
#   c0 = góra-lewo, c1 = góra-prawo, c2 = dół-prawo, c3 = dół-lewo
# Każdej krawędzi (parze rogów) przypisujemy jedną literę.
EDGE_CORNERS = {
    "A": (0, 1),  # górna krawędź markera
    "B": (1, 2),  # prawa
    "C": (2, 3),  # dolna
    "D": (3, 0),  # lewa
}

ANSWER_LABELS = list(EDGE_CORNERS.keys())


def get_dictionary():
    """Zwraca predefiniowany słownik ArUco (nowe API OpenCV >= 4.7)."""
    return cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICT_NAME))


def make_detector(strict=True):
    """Tworzy detektor markerów.

    strict=True zaostrza kryteria, żeby przypadkowe wzory w tle (plakaty,
    okładki, kratka na ubraniu) nie były brane za karty odpowiedzi.
    """
    params = cv2.aruco.DetectorParameters()
    # Subpikselowe dopracowanie rogów -> stabilniejszy odczyt obrotu.
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    if strict:
        # Mniejsza tolerancja błędów bitowych: marker musi być odczytany
        # niemal bezbłędnie, zamiast "domyślany" przez korekcje błędów.
        params.errorCorrectionRate = 0.35
        # Ramka markera musi być naprawdę czarna.
        params.maxErroneousBitsInBorderRate = 0.2
        # Odrzuca drobne śmieci i wymaga wyraźniejszego kształtu kwadratu.
        params.minMarkerPerimeterRate = 0.035
        params.polygonalApproxAccuracyRate = 0.04
        # Wyraźniejszy kontrast czarne/białe wewnątrz markera.
        params.minOtsuStdDev = 6.0
    return cv2.aruco.ArucoDetector(get_dictionary(), params)


def marker_is_black_and_white(gray, corners, min_contrast=55):
    """Sprawdza, czy w obszarze markera faktycznie jest czarno-biały wzór.

    Kolorowe/szare obrazki z tła potrafią czasem przejść detekcje. Prawdziwy
    wydrukowany marker ma silny rozdział jasności: ciemne i jasne pola.
    Zwraca False, gdy kontrast jest za słaby (czyli to nie jest karta).
    """
    pts = np.asarray(corners, dtype=np.float32).reshape(4, 2)
    side = 40
    dst = np.array([[0, 0], [side - 1, 0], [side - 1, side - 1], [0, side - 1]],
                   dtype=np.float32)
    try:
        M = cv2.getPerspectiveTransform(pts, dst)
        patch = cv2.warpPerspective(gray, M, (side, side))
    except cv2.error:
        return False
    # Próg Otsu dzieli pola na ciemne i jasne; liczymy realny rozstęp jasności.
    thr, _ = cv2.threshold(patch, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dark = patch[patch <= thr]
    light = patch[patch > thr]
    if dark.size < 20 or light.size < 20:
        return False
    return float(light.mean() - dark.mean()) >= min_contrast


def answer_from_corners(corners):
    """
    Ustala odpowiedź na podstawie 4 rogów markera.

    corners: tablica (4, 2) lub (1, 4, 2) ze współrzędnymi rogów w obrazie.
    Zwraca literę krawędzi, której środek leży najwyżej na obrazie
    (najmniejsze y) -- czyli tej krawędzi, która uczeń obrócił do góry.
    """
    pts = np.asarray(corners, dtype=np.float32).reshape(4, 2)
    best_label = None
    best_y = None
    for label, (i, j) in EDGE_CORNERS.items():
        mid_y = (pts[i][1] + pts[j][1]) / 2.0
        if best_y is None or mid_y < best_y:
            best_y = mid_y
            best_label = label
    return best_label
