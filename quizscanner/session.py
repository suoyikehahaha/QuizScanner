"""
Stan sesji quizu i logika punktacji (niezależne od interfejsu i kamery).

QuizSession trzyma aktualny quiz, fazy pytania, odpowiedzi uczniów
(dostarczane przez skaner kamery) i wyniki. Jest bezpieczny wątkowo,
bo aktualizuje go wątek kamery, a odczytuje serwer HTTP.

Fazy:
  idle     -- pytanie pokazane, jeszcze nie zbieramy odpowiedzi
  question -- zbieramy odpowiedzi z kamery (timer leci)
  reveal   -- pokazana poprawna odpowiedź + rozkład, punkty naliczone
  podium   -- ranking końcowy
"""

import random
import json
import threading
import time
import uuid

from .roster_import import (DEFAULT_CLASS_NAME, normalise_roster,
                            student_number_sort_key)

DEFAULT_QUIZ_SETTINGS = {
    "default_time": 20,        # domyślny czas nowego pytania (s)
    "default_points": 1000,    # domyślne punkty nowego pytania
    "shuffle_questions": False,
    "shuffle_answers": False,
    "show_distribution": True,  # słupki rozkładu odpowiedzi przy wyniku
    "auto_reveal_s": 6,        # tryb auto: jak długo pokazywać wynik
    "auto_gap_s": 3,           # tryb auto: przerwa przed kolejnym pytaniem
}

PHASE_IDLE = "idle"
PHASE_QUESTION = "question"
PHASE_ENDED = "ended"
PHASE_REVEAL = "reveal"
PHASE_PODIUM = "podium"

LETTERS = ["A", "B", "C", "D"]


class QuizSession:
    def __init__(self):
        self.lock = threading.RLock()
        self.quiz = {"title": "Brak wczytanego quizu", "questions": []}
        self.quiz_name = None
        self.roster_data = normalise_roster({})
        self.active_class = ""
        self.student_records = {} # stable student key -> full roster record
        self.roster = {}          # ArUco card ID -> student record for active class
        self.index = 0
        self.phase = PHASE_IDLE
        self.q_start = None
        self.q_end = None
        self.countdown_enabled = True
        self.scan_visibility = "answer"
        self.show_student_answers_on_reveal = True
        self.answers = {}         # id -> "A".."D"
        self.answer_time = {}     # id -> czas ostatniej zmiany odpowiedzi
        self.scores = {}          # id -> suma punktów
        self.awarded = False      # zabezpieczenie przed podwójnym liczeniem
        self.history = []         # wyniki per pytanie (do eksportu)
        self.speed_bonus = False  # False = punkty stałe; True = szybciej więcej
        self.only_known = True    # ignoruj ID spoza listy uczniów
        self.order = []           # kolejność pytań (może być losowa)
        self.perm = [0, 1, 2, 3]  # kolejność odpowiedzi w bieżącym pytaniu
        self.session_id = uuid.uuid4().hex
        self.attempt_id = None
        self.revision = 0
        self.on_change = None
        self.input_source = "camera"
        self.seen_events = set()
        self.on_podium = None     # wywoływane raz, gdy quiz dobiegnie końca

        # Tryb automatyczny: quiz sam odsłania wynik i przechodzi dalej.
        self.auto_mode = False
        self._auto_thread = None
        self._auto_stop = threading.Event()
        self._auto_at = None      # znacznik czasu następnego przejścia

    # ---------- konfiguracja ----------
    def settings(self):
        """Ustawienia quizu z bezpiecznymi wartościami domyślnymi."""
        s = dict(DEFAULT_QUIZ_SETTINGS)
        s.update(self.quiz.get("settings") or {})
        return s

    def load_quiz(self, quiz, name=None):
        with self.lock:
            self.end_question()
            self._changed()
            self.session_id = uuid.uuid4().hex
            self.seen_events = set()
            self.quiz = quiz
            self.quiz_name = name
            self.index = 0
            self.phase = PHASE_IDLE
            self.scores = {}
            self.history = []
            self._build_order()
            self._reset_question_state()
            self._changed()

    def _changed(self):
        with self.lock:
            self.revision += 1
            if self.on_change:
                self.on_change(self)

    def snapshot(self):
        with self.lock:
            keys = ("quiz", "quiz_name", "session_id", "attempt_id", "revision",
                    "active_class", "index", "phase", "q_start", "q_end", "order", "perm",
                    "answers", "answer_time", "scores", "awarded", "history",
                    "countdown_enabled", "scan_visibility", "show_student_answers_on_reveal",
                    "student_records", "roster_data", "input_source")
            return {key: getattr(self, key) for key in keys} | {"seen_events": sorted(self.seen_events)}

    def restore(self, data):
        with self.lock:
            for key in self.snapshot():
                if key in data and key != "seen_events":
                    setattr(self, key, data[key])
            self.seen_events = set(data.get("seen_events", []))
            self._select_active_roster()
            self._changed()

    def _build_order(self):
        """Ustala kolejność pytań (opcjonalnie losowa)."""
        n = len(self.quiz.get("questions", []))
        self.order = list(range(n))
        if self.settings().get("shuffle_questions"):
            random.shuffle(self.order)

    @staticmethod
    def student_key(student):
        return json.dumps([student.get("class_name", DEFAULT_CLASS_NAME),
                           student.get("student_no", "")],
                          ensure_ascii=False, separators=(",", ":"))

    def set_roster(self, roster):
        with self.lock:
            self.roster_data = normalise_roster(roster)
            requested_class = self.roster_data.get("active_class", "")
            if requested_class != self.active_class:
                self.end_question()
                self.phase = PHASE_IDLE
                self._reset_question_state()
            self.active_class = requested_class
            self.student_records = {
                self.student_key(student): student
                for student in self.roster_data.get("students", [])
            }
            self._select_active_roster()
            self._changed()

    def _select_active_roster(self):
        self.roster = {
            int(student["card_id"]): student
            for student in self.roster_data.get("students", [])
            if student.get("class_name") == self.active_class
        }

    def set_active_class(self, class_name):
        with self.lock:
            class_name = str(class_name or "").strip()
            if class_name not in self.roster_data.get("classes", []):
                return False
            if class_name != self.active_class:
                self.end_question()
                self.phase = PHASE_IDLE
                self._reset_question_state()
            self.active_class = class_name
            self.roster_data["active_class"] = class_name
            self._select_active_roster()
            self._changed()
            return True

    def _record_for_key(self, key):
        record = self.student_records.get(key)
        if record:
            return record
        return {"class_name": self.active_class or DEFAULT_CLASS_NAME,
                "student_no": str(key), "name": f"#{key}", "card_id": None}

    def set_speed_bonus(self, value):
        with self.lock:
            self.speed_bonus = bool(value)

    def set_countdown_enabled(self, value):
        with self.lock:
            value = bool(value)
            if not value and self.auto_mode:
                return False
            self.countdown_enabled = value
            return True

    def set_only_known(self, value):
        with self.lock:
            self.only_known = bool(value)

    def set_auto_mode(self, value):
        with self.lock:
            value = bool(value)
            if value and not self.countdown_enabled:
                return False
            self.auto_mode = value
            self._auto_at = None
            return True

    # ---------- przepływ pytania ----------
    def _reset_question_state(self):
        self.attempt_id = None
        self.answers = {}
        self.answer_time = {}
        self.q_start = None
        self.q_end = None
        self.awarded = False
        self._set_answer_perm()

    def _set_answer_perm(self):
        """Ustala kolejność wyświetlania odpowiedzi (opcjonalnie losowa).

        perm[i] = która oryginalna odpowiedź pokazujemy na pozycji i.
        Losowanie jest ustalane raz na pytanie, żeby tablica nie migotała.
        """
        self.perm = [0, 1, 2, 3]
        if self.settings().get("shuffle_answers"):
            random.shuffle(self.perm)

    def displayed_answers(self, q):
        """Odpowiedzi w kolejności pokazywanej uczniom."""
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

    def start_question(self, countdown_enabled=None):
        with self.lock:
            q = self.current_question()
            if not q:
                return False
            if self.only_known and not self.roster:
                raise ValueError("请先选择已导入学生名单的班级。")
            if self.phase == PHASE_QUESTION:
                return False
            if self.auto_mode and (countdown_enabled is False or not q.get("time", 20)):
                raise ValueError("当前题目不限时，请关闭自动模式后开始。")
            self._reset_question_state()
            self.q_start = time.time()
            t = q.get("time", 20)
            if countdown_enabled is not None:
                self.countdown_enabled = bool(countdown_enabled)
            self.q_end = self.q_start + t if t and self.countdown_enabled else None
            self.phase = PHASE_QUESTION
            self.attempt_id = uuid.uuid4().hex
            self._changed()
            return True

    def end_question(self):
        """停止收集本题答案，并在投影端显示本班作答明细。"""
        with self.lock:
            if self.phase != PHASE_QUESTION:
                return False
            q = self.current_question()
            if q and not self.awarded:
                self._award(q)
                self.awarded = True
            self.q_end = None
            self.phase = PHASE_ENDED
            self._auto_at = None
            self._changed()
            return True

    def set_scan_visibility(self, value):
        with self.lock:
            self.scan_visibility = "status" if value == "status" else "answer"

    def set_show_student_answers_on_reveal(self, value):
        with self.lock:
            self.show_student_answers_on_reveal = bool(value)

    def record_answers(self, confirmed, attempt_id=None, event_id=None):
        """confirmed: dict {id: 'A'/'B'/'C'/'D'} z potwierdzonymi odczytami.
        Wywoływane przez wątek kamery. Zapisuje odpowiedzi i czas zmiany."""
        with self.lock:
            if self.phase != PHASE_QUESTION:
                return False
            if attempt_id is not None and attempt_id != self.attempt_id:
                return False
            if event_id and event_id in self.seen_events:
                return True
            if self.q_end and time.time() > self.q_end:
                return  # czas minął -> zamrażamy odpowiedzi
            now = time.time()
            changed = False
            for mid, ans in confirmed.items():
                mid = int(mid)
                # Ochrona przed przypadkowymi wykryciami: przyjmuj tylko ID,
                # które faktycznie są na liście uczniów.
                if self.only_known and mid not in self.roster:
                    continue
                if ans not in LETTERS:
                    continue
                student = self.roster.get(mid)
                if student:
                    key = self.student_key(student)
                else:
                    key = self.student_key({"class_name": self.active_class or DEFAULT_CLASS_NAME,
                                            "student_no": str(mid)})
                if self.answers.get(key) != ans:
                    changed = True
                    self.answers[key] = ans
                    self.answer_time[key] = now
            if event_id:
                self.seen_events.add(event_id)
            if changed or event_id:
                self._changed()
            return True

    def time_left(self):
        if self.phase == PHASE_QUESTION and self.q_end:
            return max(0.0, self.q_end - time.time())
        return None

    def reveal(self):
        with self.lock:
            q = self.current_question()
            if not q or self.phase not in (PHASE_QUESTION, PHASE_ENDED, PHASE_REVEAL):
                return
            if not self.awarded:
                self._award(q)
                self.awarded = True
            self.phase = PHASE_REVEAL
            self._changed()

    def _award(self, q):
        # Uczniowie odpowiadają litera z TABLICY, więc liczy się pozycja
        # po ewentualnym przetasowaniu odpowiedzi.
        correct = self.displayed_correct(q)
        base = int(q.get("points", 1000) or 0)
        t = float(q.get("time", 20) or 20)
        letter = LETTERS[correct] if isinstance(correct, int) and 0 <= correct < 4 else None
        shown = self.displayed_answers(q)
        result = {
            "session_id": self.session_id,
            "class_name": self.active_class,
            "attempt_id": self.attempt_id,
            "question_id": self.order[self.index],
            "index": self.index,
            "question": q.get("text", ""),
            "options": shown,
            "correct": letter,
            "correct_text": shown[correct] if letter else "",
            "points_max": base,
            "answers": {},
        }
        for mid, ans in self.answers.items():
            is_correct = letter is not None and ans == letter
            pts = 0
            if is_correct and base > 0:
                if self.speed_bonus:
                    # Styl Kahoot: kto szybciej ustalił odpowiedź, dostaje więcej.
                    elapsed = self.answer_time.get(mid, self.q_start) - self.q_start
                    frac = 1.0 - min(max(elapsed / t, 0.0), 1.0)
                    pts = int(round(base * (0.5 + 0.5 * frac)))
                else:
                    # Punkty stałe: każda poprawna odpowiedź warta tyle samo.
                    pts = base
            result["answers"][mid] = {"answer": ans, "correct": is_correct, "points": pts}
        self.history.append(result)
        latest = {}
        for item in self.history:
            latest[(item.get("class_name", self.active_class), item.get("question_id", item["index"]))] = item
        self.scores = {}
        for item in latest.values():
            for key, answer in item["answers"].items():
                self.scores[key] = self.scores.get(key, 0) + answer["points"]

    def move_and_start(self, direction):
        with self.lock:
            if direction == "prev" and self.index <= 0:
                return False
            if self.only_known and not self.roster:
                raise ValueError("请先选择已导入学生名单的班级。")
            self.end_question()
            (self.prev_question if direction == "prev" else self.next_question)()
            if self.phase != PHASE_PODIUM:
                self.start_question()
            return True

    def next_question(self):
        with self.lock:
            self.end_question()
            if self.index < len(self.quiz["questions"]) - 1:
                self.index += 1
                self.phase = PHASE_IDLE
                self._reset_question_state()
                self._changed()
                return
            finished = self.phase != PHASE_PODIUM
            self.phase = PHASE_PODIUM
            self._changed()
        # ponytail: raport zapisujemy tu, w wątku wywołującym -- to ułamek
        # sekundy; osobny wątek dopiero gdyby doszły ciężkie formaty.
        if finished and self.on_podium:
            try:
                self.on_podium(self)
            except Exception:
                pass

    def prev_question(self):
        with self.lock:
            self.end_question()
            if self.index > 0:
                self.index -= 1
                self.phase = PHASE_IDLE
                self._reset_question_state()
            self._changed()

    def goto(self, idx):
        with self.lock:
            self.end_question()
            if 0 <= idx < len(self.quiz["questions"]):
                self.index = idx
                self.phase = PHASE_IDLE
                self._reset_question_state()
            self._changed()

    def reset_scores(self):
        with self.lock:
            self.end_question()
            self._changed()
            self.session_id = uuid.uuid4().hex
            self.seen_events = set()
            self.scores = {}
            self.history = []
            self.index = 0
            self.phase = PHASE_IDLE
            self._reset_question_state()
            self._changed()

    # Skróty używane przez pętlę automatyczna (lock jest reentrantny).
    def _do_reveal(self):
        self.reveal()

    def _do_next(self):
        self.next_question()

    def _do_start(self):
        self.start_question()

    # ---------- tryb automatyczny ----------
    def start_auto_engine(self):
        """Uruchamia wątek prowadzący quiz samodzielnie (gdy auto_mode=True)."""
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
                pass  # tryb auto nigdy nie może wywrócić aplikacji

    def _auto_tick(self):
        with self.lock:
            if not self.auto_mode and self.phase == PHASE_QUESTION and self.q_end and time.time() >= self.q_end:
                self.end_question()
            if not self.auto_mode or self.phase == PHASE_PODIUM:
                self._auto_at = None
                return
            st = self.settings()
            now = time.time()

            if self.phase == PHASE_QUESTION:
                # Czas pytania minął -> pokaż wynik.
                if self.q_end and now >= self.q_end:
                    self._do_reveal()
                    self._auto_at = now + float(st.get("auto_reveal_s", 6) or 0)
                return

            if self.phase == PHASE_REVEAL:
                # Po pokazaniu wyniku -> następne pytanie (lub podium).
                if self._auto_at and now >= self._auto_at:
                    self._do_next()
                    self._auto_at = (now + float(st.get("auto_gap_s", 3) or 0)
                                     if self.phase != PHASE_PODIUM else None)
                return

            if self.phase == PHASE_IDLE:
                # Krótka przerwa między pytaniami, potem start kolejnego.
                if self._auto_at is None:
                    self._auto_at = now + float(st.get("auto_gap_s", 3) or 0)
                elif now >= self._auto_at:
                    self._do_start()
                    self._auto_at = None

    def auto_next_in(self):
        """Ile sekund do automatycznego przejścia (None, gdy nie dotyczy)."""
        if self.auto_mode and self._auto_at:
            return max(0.0, self._auto_at - time.time())
        return None

    def leaderboard(self, top=None):
        items = [item for item in self.scores.items()
                 if self._record_for_key(item[0]).get("class_name") == self.active_class]
        items.sort(key=lambda item: (-item[1],
                                     student_number_sort_key(
                                         self._record_for_key(item[0]).get("student_no", ""))))
        board = []
        for key, score in items:
            student = self._record_for_key(key)
            board.append({"key": key, "id": student.get("student_no", ""),
                          "student_no": student.get("student_no", ""),
                          "class_name": student.get("class_name", ""),
                          "card_id": student.get("card_id"),
                          "name": student.get("name", ""), "score": score})
        return board[:top] if top else board

    # ---------- widok stanu ----------
    def state(self, full=False, include_students=False):
        """Słownik stanu do JSON. full=True (nauczyciel) dołącza poprawna
        odpowiedź zawsze; dla tablicy tylko w fazie reveal."""
        with self.lock:
            q = self.current_question()
            tl = self.time_left()
            dist = {"A": 0, "B": 0, "C": 0, "D": 0}
            active_answers = {
                key: answer for key, answer in self.answers.items()
                if self._record_for_key(key).get("class_name") == self.active_class
            }
            per_student = {}
            for key, a in active_answers.items():
                if a in dist:
                    dist[a] += 1
                per_student[key] = a
            public_status_only = (include_students and not full and
                                  self.scan_visibility == "status" and
                                  self.phase == PHASE_QUESTION)
            st = {
                "session_id": self.session_id,
                "attempt_id": self.attempt_id,
                "revision": self.revision,
                "input_source": self.input_source,
                "quiz_title": self.quiz.get("title", ""),
                "quiz_name": self.quiz_name,
                "index": self.index,
                "total": len(self.quiz["questions"]),
                "phase": self.phase,
                "active_class": self.active_class,
                "classes": list(self.roster_data.get("classes", [])),
                "countdown_enabled": self.countdown_enabled,
                "scan_visibility": self.scan_visibility,
                "show_student_answers_on_reveal": self.show_student_answers_on_reveal,
                "time_left": round(tl, 1) if tl is not None else None,
                "answered": len(active_answers),
                "distribution": ({letter: 0 for letter in LETTERS}
                                 if public_status_only else dist),
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
                    "material": q.get("material", ""),
                    "answers": self.displayed_answers(q),
                    "time": q.get("time", 20),
                    "points": q.get("points", 1000),
                    "media": q.get("media") or None,
                    "slide": q.get("slide") or {},
                }
                if full or self.phase == PHASE_REVEAL:
                    qd["correct"] = self.displayed_correct(q)
                st["question"] = qd
            if full:
                st["students"] = {
                    key: {"key": key,
                          "name": self._record_for_key(key).get("name", ""),
                          "student_no": self._record_for_key(key).get("student_no", ""),
                          "class_name": self._record_for_key(key).get("class_name", ""),
                          "card_id": self._record_for_key(key).get("card_id"),
                          "answer": answer}
                    for key, answer in per_student.items()
                }
                st["scores"] = {
                    key: score for key, score in self.scores.items()
                    if self._record_for_key(key).get("class_name") == self.active_class
                }
                st["speed_bonus"] = self.speed_bonus
                st["only_known"] = self.only_known
            if include_students and self.phase in (PHASE_QUESTION, PHASE_ENDED, PHASE_REVEAL):
                # 开始作答前不向投影端暴露名单；名单始终来自当前选择班级。
                # status 模式仅返回是否扫到；结束作答后显示完整答案明细。
                show_answers = (full or
                                (self.phase == PHASE_QUESTION and self.scan_visibility == "answer") or
                                self.phase == PHASE_ENDED or
                                (self.phase == PHASE_REVEAL and self.show_student_answers_on_reveal))
                ordered_students = sorted(self.roster.items(), key=lambda item: (
                    student_number_sort_key(item[1].get("student_no", "")),
                    item[1].get("name", "").casefold()))
                st["live_students"] = [
                    {
                        "key": self.student_key(student),
                        "id": str(student.get("student_no", "")),
                        "student_no": str(student.get("student_no", "")),
                        "class_name": student.get("class_name", ""),
                        "card_id": mid,
                        "name": student.get("name", ""),
                        "scanned": self.student_key(student) in per_student,
                        "answer": (per_student.get(self.student_key(student))
                                   if show_answers else None),
                    }
                    for mid, student in ordered_students
                ]
                st["roster_total"] = len(self.roster)
            return st
