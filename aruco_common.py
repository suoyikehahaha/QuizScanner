"""
Wspolna konfiguracja i logika ArUco dla generatora kart i skanera.

Zasada dzialania (jak Plickers):
- Kazda karta ma jeden marker ArUco o unikalnym ID  =  konkretny uczen.
- Karta ma 4 krawedzie opisane literami A / B / C / D.
- Uczen obraca karte tak, aby wybrana litera byla u gory.
- Skaner wykrywa marker, ustala ktora krawedz jest najwyzej na obrazie
  i odczytuje z tego odpowiedz. Jeden kadr = wiele uczniow naraz.

Ten sam slownik markerow MUSI byc uzyty w generatorze i w skanerze,
dlatego oba pliki importuja stad DICT_NAME i EDGE_CORNERS.
"""

import cv2
import numpy as np

# Slownik ArUco. 4x4_250 = do 250 unikalnych ID (uczniow),
# male markery czytelne z duzej odleglosci. W razie potrzeby zmien tutaj
# w OBU miejscach naraz (generator i skaner uzywaja tej stalej).
DICT_NAME = "DICT_4X4_250"

# Litery odpowiedzi przypisane do krawedzi markera.
# detectMarkers zwraca rogi ZAWSZE w kanonicznej kolejnosci markera
# (niezaleznie od fizycznego obrotu karty), gdzie:
#   c0 = gora-lewo, c1 = gora-prawo, c2 = dol-prawo, c3 = dol-lewo
# Kazdej krawedzi (parze rogow) przypisujemy jedna litere.
EDGE_CORNERS = {
    "A": (0, 1),  # gorna krawedz markera
    "B": (1, 2),  # prawa
    "C": (2, 3),  # dolna
    "D": (3, 0),  # lewa
}

ANSWER_LABELS = list(EDGE_CORNERS.keys())


def get_dictionary():
    """Zwraca predefiniowany slownik ArUco (nowe API OpenCV >= 4.7)."""
    return cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICT_NAME))


def make_detector(strict=True):
    """Tworzy detektor markerow.

    strict=True zaostrza kryteria, zeby przypadkowe wzory w tle (plakaty,
    okladki, kratka na ubraniu) nie byly brane za karty odpowiedzi.
    """
    params = cv2.aruco.DetectorParameters()
    # Subpikselowe dopracowanie rogow -> stabilniejszy odczyt obrotu.
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    if strict:
        # Mniejsza tolerancja bledow bitowych: marker musi byc odczytany
        # niemal bezblednie, zamiast "domyslany" przez korekcje bledow.
        params.errorCorrectionRate = 0.35
        # Ramka markera musi byc naprawde czarna.
        params.maxErroneousBitsInBorderRate = 0.2
        # Odrzuca drobne smieci i wymaga wyrazniejszego ksztaltu kwadratu.
        params.minMarkerPerimeterRate = 0.035
        params.polygonalApproxAccuracyRate = 0.04
        # Wyrazniejszy kontrast czarne/biale wewnatrz markera.
        params.minOtsuStdDev = 6.0
    return cv2.aruco.ArucoDetector(get_dictionary(), params)


def marker_is_black_and_white(gray, corners, min_contrast=55):
    """Sprawdza, czy w obszarze markera faktycznie jest czarno-bialy wzor.

    Kolorowe/szare obrazki z tla potrafia czasem przejsc detekcje. Prawdziwy
    wydrukowany marker ma silny rozdzial jasnosci: ciemne i jasne pola.
    Zwraca False, gdy kontrast jest za slaby (czyli to nie jest karta).
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
    # Prog Otsu dzieli pola na ciemne i jasne; liczymy realny rozstep jasnosci.
    thr, _ = cv2.threshold(patch, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dark = patch[patch <= thr]
    light = patch[patch > thr]
    if dark.size < 20 or light.size < 20:
        return False
    return float(light.mean() - dark.mean()) >= min_contrast


def answer_from_corners(corners):
    """
    Ustala odpowiedz na podstawie 4 rogow markera.

    corners: tablica (4, 2) lub (1, 4, 2) ze wspolrzednymi rogow w obrazie.
    Zwraca litere krawedzi, ktorej srodek lezy najwyzej na obrazie
    (najmniejsze y) -- czyli tej krawedzi, ktora uczen obrocil do gory.
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
