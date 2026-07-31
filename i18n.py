"""
Teksty aplikacji po stronie Pythona (karty do druku, eksport wynikow).

Interfejs webowy ma wlasny slownik w web/i18n.js -- tutaj sa tylko napisy,
ktore powstaja w Pythonie. Domyslny jezyk: polski.
"""

DEFAULT_LANG = "pl"

STRINGS = {
    "pl": {
        "card_hint": "Obróć wybraną literę do góry i podnieś kartę",
        "card_student": "Uczeń",
        "results_place": "miejsce",
        "results_id": "id",
        "results_name": "imię i nazwisko",
        "results_points": "punkty",
        "results_answer": "odpowiedź",
        "results_question": "pytanie",
        "results_correct": "poprawna",
    },
    "en": {
        "card_hint": "Turn your chosen letter to the top and hold the card up",
        "card_student": "Student",
        "results_place": "place",
        "results_id": "id",
        "results_name": "name",
        "results_points": "points",
        "results_answer": "answer",
        "results_question": "question",
        "results_correct": "correct",
    },
}


def t(key, lang=DEFAULT_LANG):
    """Zwraca napis w wybranym jezyku (z awaryjnym powrotem do polskiego)."""
    table = STRINGS.get(lang) or STRINGS[DEFAULT_LANG]
    return table.get(key) or STRINGS[DEFAULT_LANG].get(key, key)
