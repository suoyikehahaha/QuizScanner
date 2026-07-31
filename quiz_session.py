"""
Stan sesji quizu i logika punktacji (niezalezne od interfejsu i kamery).

QuizSession trzyma aktualny quiz, fazy pytania, odpowiedzi uczniow
(dostarczane przez skaner kamery) i wyniki. Jest bezpieczny watkowo,
bo aktualizuje go watek kamery, a odczytuje serwer HTTP.

Fazy:
  idle     -- pytanie pokazane, jeszcze nie zbieramy odpowiedzi
  question -- zbieramy odpowiedzi z kamery (timer leci)
  reveal   -- pokazana poprawna odpowiedz + rozklad, punkty naliczone
  podium   -- ranking koncowy
"""

import random
import threading
import time

DEFAULT_QUIZ_SETTINGS = {
    "default_time": 20,        # domyslny czas nowego pytania (s)
    "default_points": 1000,    # domyslne punkty nowego pytania
    "shuffle_questions": False,
    "shuffle_answers": False,
    "show_distribution": True,  # slupki rozkladu odpowiedzi przy wyniku
    "auto_reveal_s": 6,        # tryb auto: jak dlugo pokazywac wynik
    "auto_gap_s": 3,           # tryb auto: przerwa przed kolejnym pytaniem
}

PHASE_IDLE = "idle"
PHASE_QUESTION = "question"
PHASE_REVEAL = "reveal"
PHASE_PODIUM = "podium"

LETTERS = ["A", "B", "C", "D"]


class QuizSession:
    def __init__(self):
        self.lock = threading.RLock()
        self.quiz = {"title": "Brak wczytanego quizu", "questions": []}
        self.quiz_name = None
        self.roster = {}          # id(int) -> imie
        self.index = 0
        self.phase = PHASE_IDLE
        self.q_start = None
        self.q_end = None
        self.answers = {}         # id -> "A".."D"
        self.answer_time = {}     # id -> czas ostatniej zmiany odpowiedzi
        self.scores = {}          # id -> suma punktow
        self.awarded = False      # zabezpieczenie przed podwojnym liczeniem
        self.history = []         # wyniki per pytanie (do eksportu)
        self.speed_bonus = False  # False = punkty stale; True = szybciej wiecej
        self.only_known = True    # ignoruj ID spoza listy uczniow
        self.order = []           # kolejnosc pytan (moze byc losowa)
        self.perm = [0, 1, 2, 3]  # kolejnosc odpowiedzi w biezacym pytaniu

        # Tryb automatyczny: quiz sam odslania wynik i przechodzi dalej.
        self.auto_mode = False
        self._auto_thread = None
        self._auto_stop = threading.Event()
        self._auto_at = None      # znacznik czasu nastepnego przejscia

    # ---------- konfiguracja ----------
    def settings(self):
        """Ustawienia quizu z bezpiecznymi wartosciami domyslnymi."""
        s = dict(DEFAULT_QUIZ_SETTINGS)
        s.update(self.quiz.get("settings") or {})
        return s

    def load_quiz(self, quiz, name=None):
        with self.lock:
            self.quiz = quiz
            self.quiz_name = name
            self.index = 0
            self.phase = PHASE_IDLE
            self.scores = {}
            self.history = []
            self._build_order()
            self._reset_question_state()

    def _build_order(self):
        """Ustala kolejnosc pytan (opcjonalnie losowa)."""
        n = len(self.quiz.get("questions", []))
        self.order = list(range(n))
        if self.settings().get("shuffle_questions"):
            random.shuffle(self.order)

    def set_roster(self, roster):
        with self.lock:
            self.roster = {int(k): v for k, v in roster.items()}

    def set_speed_bonus(self, value):
        with self.lock:
            self.speed_bonus = bool(value)

    def set_only_known(self, value):
        with self.lock:
            self.only_known = bool(value)

    def set_auto_mode(self, value):
        with self.lock:
            self.auto_mode = bool(value)
            self._auto_at = None

    # ---------- przeplyw pytania ----------
    def _reset_question_state(self):
        self.answers = {}
        self.answer_time = {}
        self.q_start = None
        self.q_end = None
        self.awarded = False
        self._set_answer_perm()

    def _set_answer_perm(self):
        """Ustala kolejnosc wyswietlania odpowiedzi (opcjonalnie losowa).

        perm[i] = ktora oryginalna odpowiedz pokazujemy na pozycji i.
        Losowanie jest ustalane raz na pytanie, zeby tablica nie migotala.
        """
        self.perm = [0, 1, 2, 3]
        if self.settings().get("shuffle_answers"):
            random.shuffle(self.perm)

    def displayed_answers(self, q):
        """Odpowiedzi w kolejnosci pokazywanej uczniom."""
        src = list(q.get("answers", ["", "", "", ""]))
        src += [""] * (4 - len(src))
        return [src[i] for i in self.perm]

    def displayed_correct(self, q):
        """Indeks poprawnej odpowiedzi PO ewentualnym przetasowaniu."""
        c = q.get("correct", None)
        if not isinstance(c, int) or not (0 <= c < 4):
            return None
        try:
            return self.perm.index(c)
        except ValueError:
            return c

    def current_question(self):
        qs = self.quiz.get("questions", [])
        if not self.order or len(self.order) != len(qs):
            self._build_order()
        if 0 <= self.index < len(self.order):
            real = self.order[self.index]
            if 0 <= real < len(qs):
                return qs[real]
        return None

    def start_question(self):
        with self.lock:
            q = self.current_question()
            if not q:
                return
            self._reset_question_state()
            self.q_start = time.time()
            t = q.get("time", 20)
            self.q_end = self.q_start + t if t else None
            self.phase = PHASE_QUESTION

    def record_answers(self, confirmed):
        """confirmed: dict {id: 'A'/'B'/'C'/'D'} z potwierdzonymi odczytami.
        Wywolywane przez watek kamery. Zapisuje odpowiedzi i czas zmiany."""
        with self.lock:
            if self.phase != PHASE_QUESTION:
                return
            if self.q_end and time.time() > self.q_end:
                return  # czas minal -> zamrazamy odpowiedzi
            now = time.time()
            for mid, ans in confirmed.items():
                # Ochrona przed przypadkowymi wykryciami: przyjmuj tylko ID,
                # ktore faktycznie sa na liscie uczniow.
                if self.only_known and self.roster and mid not in self.roster:
                    continue
                if self.answers.get(mid) != ans:
                    self.answers[mid] = ans
                    self.answer_time[mid] = now

    def time_left(self):
        if self.phase == PHASE_QUESTION and self.q_end:
            return max(0.0, self.q_end - time.time())
        return None

    def reveal(self):
        with self.lock:
            q = self.current_question()
            if not q:
                return
            if not self.awarded:
                self._award(q)
                self.awarded = True
            self.phase = PHASE_REVEAL

    def _award(self, q):
        # Uczniowie odpowiadaja litera z TABLICY, wiec liczy sie pozycja
        # po ewentualnym przetasowaniu odpowiedzi.
        correct = self.displayed_correct(q)
        base = int(q.get("points", 1000) or 0)
        t = float(q.get("time", 20) or 20)
        letter = LETTERS[correct] if isinstance(correct, int) and 0 <= correct < 4 else None
        result = {"question": q.get("text", ""), "correct": letter, "answers": {}}
        for mid, ans in self.answers.items():
            is_correct = letter is not None and ans == letter
            pts = 0
            if is_correct and base > 0:
                if self.speed_bonus:
                    # Styl Kahoot: kto szybciej ustalil odpowiedz, dostaje wiecej.
                    elapsed = self.answer_time.get(mid, self.q_start) - self.q_start
                    frac = 1.0 - min(max(elapsed / t, 0.0), 1.0)
                    pts = int(round(base * (0.5 + 0.5 * frac)))
                else:
                    # Punkty stale: kazda poprawna odpowiedz warta tyle samo.
                    pts = base
            self.scores[mid] = self.scores.get(mid, 0) + pts
            result["answers"][mid] = {"answer": ans, "correct": is_correct, "points": pts}
        self.history.append(result)

    def next_question(self):
        with self.lock:
            if self.index < len(self.quiz["questions"]) - 1:
                self.index += 1
                self.phase = PHASE_IDLE
                self._reset_question_state()
            else:
                self.phase = PHASE_PODIUM

    def prev_question(self):
        with self.lock:
            if self.index > 0:
                self.index -= 1
                self.phase = PHASE_IDLE
                self._reset_question_state()

    def goto(self, idx):
        with self.lock:
            if 0 <= idx < len(self.quiz["questions"]):
                self.index = idx
                self.phase = PHASE_IDLE
                self._reset_question_state()

    def reset_scores(self):
        with self.lock:
            self.scores = {}
            self.history = []
            self.index = 0
            self.phase = PHASE_IDLE
            self._reset_question_state()

    # Skroty uzywane przez petle automatyczna (lock jest reentrantny).
    def _do_reveal(self):
        self.reveal()

    def _do_next(self):
        self.next_question()

    def _do_start(self):
        self.start_question()

    # ---------- tryb automatyczny ----------
    def start_auto_engine(self):
        """Uruchamia watek prowadzacy quiz samodzielnie (gdy auto_mode=True)."""
        if self._auto_thread and self._auto_thread.is_alive():
            return
        self._auto_stop.clear()
        self._auto_thread = threading.Thread(target=self._auto_loop, daemon=True)
        self._auto_thread.start()

    def stop_auto_engine(self):
        self._auto_stop.set()

    def _auto_loop(self):
        while not self._auto_stop.wait(0.2):
            try:
                self._auto_tick()
            except Exception:
                pass  # tryb auto nigdy nie moze wywrocic aplikacji

    def _auto_tick(self):
        with self.lock:
            if not self.auto_mode or self.phase == PHASE_PODIUM:
                self._auto_at = None
                return
            st = self.settings()
            now = time.time()

            if self.phase == PHASE_QUESTION:
                # Czas pytania minal -> pokaz wynik.
                if self.q_end and now >= self.q_end:
                    self._do_reveal()
                    self._auto_at = now + float(st.get("auto_reveal_s", 6) or 0)
                return

            if self.phase == PHASE_REVEAL:
                # Po pokazaniu wyniku -> nastepne pytanie (lub podium).
                if self._auto_at and now >= self._auto_at:
                    self._do_next()
                    self._auto_at = (now + float(st.get("auto_gap_s", 3) or 0)
                                     if self.phase != PHASE_PODIUM else None)
                return

            if self.phase == PHASE_IDLE:
                # Krotka przerwa miedzy pytaniami, potem start kolejnego.
                if self._auto_at is None:
                    self._auto_at = now + float(st.get("auto_gap_s", 3) or 0)
                elif now >= self._auto_at:
                    self._do_start()
                    self._auto_at = None

    def auto_next_in(self):
        """Ile sekund do automatycznego przejscia (None, gdy nie dotyczy)."""
        if self.auto_mode and self._auto_at:
            return max(0.0, self._auto_at - time.time())
        return None

    def leaderboard(self, top=None):
        items = sorted(self.scores.items(), key=lambda kv: kv[1], reverse=True)
        board = [{"id": mid, "name": self.roster.get(mid, f"#{mid}"), "score": sc}
                 for mid, sc in items]
        return board[:top] if top else board

    # ---------- widok stanu ----------
    def state(self, full=False):
        """Slownik stanu do JSON. full=True (nauczyciel) dolacza poprawna
        odpowiedz zawsze; dla tablicy tylko w fazie reveal."""
        with self.lock:
            q = self.current_question()
            tl = self.time_left()
            dist = {"A": 0, "B": 0, "C": 0, "D": 0}
            per_student = {}
            for mid, a in self.answers.items():
                if a in dist:
                    dist[a] += 1
                per_student[mid] = a
            st = {
                "quiz_title": self.quiz.get("title", ""),
                "quiz_name": self.quiz_name,
                "index": self.index,
                "total": len(self.quiz["questions"]),
                "phase": self.phase,
                "time_left": round(tl, 1) if tl is not None else None,
                "answered": len(self.answers),
                "distribution": dist,
                "question": None,
                "leaderboard": self.leaderboard(top=10),
                "auto_mode": self.auto_mode,
                "auto_next_in": (round(self.auto_next_in(), 1)
                                 if self.auto_next_in() is not None else None),
                "show_distribution": bool(self.settings().get("show_distribution", True)),
            }
            if q:
                qd = {
                    "text": q.get("text", ""),
                    "answers": self.displayed_answers(q),
                    "time": q.get("time", 20),
                    "points": q.get("points", 1000),
                    "media": q.get("media") or None,
                }
                if full or self.phase == PHASE_REVEAL:
                    qd["correct"] = self.displayed_correct(q)
                st["question"] = qd
            if full:
                st["students"] = {
                    str(mid): {"name": self.roster.get(mid, f"#{mid}"), "answer": a}
                    for mid, a in per_student.items()
                }
                st["scores"] = {str(k): v for k, v in self.scores.items()}
                st["speed_bonus"] = self.speed_bonus
                st["only_known"] = self.only_known
            return st
