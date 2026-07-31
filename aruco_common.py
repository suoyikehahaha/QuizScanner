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


def make_detector():
    """Tworzy detektor markerow z domyslnymi parametrami."""
    params = cv2.aruco.DetectorParameters()
    # Subpikselowe dopracowanie rogow -> stabilniejszy odczyt obrotu.
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    return cv2.aruco.ArucoDetector(get_dictionary(), params)


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
