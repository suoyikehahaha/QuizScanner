"""
Teksty aplikacji po stronie Pythona (karty do druku, eksport wyników).

Interfejs webowy ma własny słownik w web/i18n.js -- tutaj są tylko napisy,
które powstają w Pythonie. Domyślny język: uproszczony chiński.
"""

DEFAULT_LANG = "zh"

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
    "zh": {
        "card_hint": "将所选选项转到朝上位置并举起答题卡",
        "card_student": "学生",
        "results_place": "名次",
        "results_id": "编号",
        "results_name": "姓名",
        "results_points": "得分",
        "results_answer": "答案",
        "results_question": "题目",
        "results_correct": "正确答案",
    },
}


def t(key, lang=DEFAULT_LANG):
    """Returns a localized Python-generated string, falling back to Chinese."""
    table = STRINGS.get(lang) or STRINGS[DEFAULT_LANG]
    return table.get(key) or STRINGS[DEFAULT_LANG].get(key, key)
