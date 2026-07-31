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

import threading
import time

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
        self.speed_bonus = False  # False = punkty stale; True = szybciej wiecej (styl Kahoot)

    # ---------- konfiguracja ----------
    def load_quiz(self, quiz, name=None):
        with self.lock:
            self.quiz = quiz
            self.quiz_name = name
            self.index = 0
            self.phase = PHASE_IDLE
            self.scores = {}
            self.history = []
            self._reset_question_state()

    def set_roster(self, roster):
        with self.lock:
            self.roster = {int(k): v for k, v in roster.items()}

    def set_speed_bonus(self, value):
        with self.lock:
            self.speed_bonus = bool(value)

    # ---------- przeplyw pytania ----------
    def _reset_question_state(self):
        self.answers = {}
        self.answer_time = {}
        self.q_start = None
        self.q_end = None
        self.awarded = False

    def current_question(self):
        if 0 <= self.index < len(self.quiz["questions"]):
            return self.quiz["questions"][self.index]
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
        correct = q.get("correct", None)
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
            }
            if q:
                qd = {
                    "text": q.get("text", ""),
                    "answers": q.get("answers", ["", "", "", ""]),
                    "time": q.get("time", 20),
                    "points": q.get("points", 1000),
                }
                if full or self.phase == PHASE_REVEAL:
                    qd["correct"] = q.get("correct", None)
                st["question"] = qd
            if full:
                st["students"] = {
                    str(mid): {"name": self.roster.get(mid, f"#{mid}"), "answer": a}
                    for mid, a in per_student.items()
                }
                st["scores"] = {str(k): v for k, v in self.scores.items()}
                st["speed_bonus"] = self.speed_bonus
            return st
