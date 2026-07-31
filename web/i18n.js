// Tlumaczenia interfejsu. Domyslny jezyk: polski.
// Uzycie w HTML:  <span data-i18n="klucz"></span>  (albo data-i18n-ph dla placeholder)
// Uzycie w JS:    t("klucz")  /  t("klucz", {n: 1, total: 4})

const I18N = {
  pl: {
    // --- wspolne ---
    app_name: "QuizScanner",
    lang_label: "Język",
    yes: "Tak", no: "Nie",
    save: "Zapisz", cancel: "Anuluj", delete: "Usuń", close: "Zamknij",

    // --- panel nauczyciela ---
    t_load: "Wczytaj",
    t_editor: "✏️ Edytor",
    t_board: "📺 Tablica",
    t_export: "⬇ Eksport wyników",
    t_no_quizzes: "— brak quizów, użyj edytora —",
    t_lan_board: "Tablica w sieci",
    t_cam_title: "Podgląd kamery (skaner)",
    t_cam_hint: "Uczniowie obracają kartę wybraną literą do góry.",
    t_cam_wait: "⏳ Kamera się uruchamia lub jest niedostępna (sprawdź źródło).",
    t_cam_source: "Źródło obrazu",
    t_cam_apply: "Przełącz",
    t_cam_source_hint: "Numer kamery (0, 1, 2…) albo adres telefonu, np. http://192.168.1.50:8080/video",
    t_phone_help: "📱 Jak podłączyć telefon?",
    t_question_of: "Pytanie {n} / {total}",
    t_start: "▶ Start pytania",
    t_reveal: "✓ Pokaż wynik",
    t_prev: "◀ Poprzednie",
    t_next: "Następne ▶",
    t_reset: "⟲ Reset punktów",
    t_stat_time: "Czas",
    t_stat_answered: "Odpowiedziało",
    t_stat_dist: "A/B/C/D",
    t_speed_label: "Punkty za szybkość",
    t_speed_sub: "Wył. = każda poprawna odpowiedź warta tyle samo. Wł. = szybciej daje więcej.",
    t_auto_label: "Tryb automatyczny",
    t_auto_sub: "Po starcie quiz sam pokazuje wyniki i przechodzi dalej — bez klikania.",
    t_auto_running: "Tryb automatyczny działa — quiz prowadzi się sam.",
    t_students_live: "Odpowiedzi uczniów na żywo",
    t_col_id: "ID", t_col_student: "Uczeń", t_col_answer: "Odpowiedź", t_col_points: "Punkty",
    t_no_answers: "Brak odpowiedzi",
    t_ranking: "Ranking",
    t_no_results: "Brak wyników",
    t_load_quiz_first: "Wczytaj quiz, aby rozpocząć.",
    t_confirm_reset: "Wyzerować punkty i zacząć od nowa?",
    t_saved_results: "Zapisano wyniki:",
    t_only_known: "Tylko uczniowie z listy",
    t_only_known_sub: "Ignoruje kody spoza listy — chroni przed przypadkowymi wykryciami w tle.",

    // --- tablica ---
    b_question_of: "Pytanie {n} z {total}",
    b_scanned: "Zeskanowano:",
    b_correct: "Poprawna:",
    b_prepare: "Przygotuj kartę — obróć wybraną literę (A/B/C/D) do góry",
    b_ready: "Gotowi do startu",
    b_load_hint: "Wczytaj quiz w panelu nauczyciela",
    b_end_kicker: "Koniec quizu",
    b_standings: "Klasyfikacja",
    b_no_results: "Brak wyników",

    // --- edytor ---
    e_title: "QuizScanner · Edytor",
    e_tab_quiz: "Quizy",
    e_tab_roster: "Uczniowie",
    e_tab_settings: "Ustawienia",
    e_to_teacher: "← Panel nauczyciela",
    e_quizzes: "Quizy",
    e_new_quiz: "+ Nowy quiz",
    e_no_quizzes: "Brak quizów — utwórz nowy",
    e_quiz_title: "Tytuł quizu",
    e_quiz_title_ph: "np. Powtórka z historii",
    e_save: "💾 Zapisz",
    e_duplicate: "⧉ Duplikuj",
    e_delete: "🗑 Usuń",
    e_export_file: "⬇ Zapisz do pliku",
    e_import_file: "⬆ Wczytaj z pliku",
    e_file_hint: "Plik .quiz możesz wysłać innemu nauczycielowi.",
    e_editing_file: "plik:",
    e_unsaved: "(nowy, niezapisany)",
    e_question_n: "Pytanie {n}",
    e_question_ph: "Treść pytania…",
    e_answer_ph: "Odpowiedź {letter}",
    e_correct: "poprawna",
    e_time_s: "Czas (s)",
    e_points: "Punkty (maks)",
    e_add_question: "+ Dodaj pytanie",
    e_media: "Zdjęcie / film",
    e_media_add: "🖼 Dodaj plik",
    e_media_remove: "✕ Usuń plik",
    e_media_hint: "Obraz (JPG/PNG/GIF/WEBP) lub film (MP4/WEBM) — pokaże się na tablicy przy pytaniu.",
    e_media_too_big: "Plik jest za duży (limit {mb} MB).",
    e_media_bad_type: "Nieobsługiwany typ pliku.",
    e_roster_hint: "ID = numer markera na wydrukowanej karcie.",
    e_save_roster: "💾 Zapisz listę",
    e_add_student: "+ Dodaj ucznia",
    e_cards_pdf: "📄 Pobierz karty (PDF)",
    e_cards_hint: "Karty do druku dla powyższej listy — jedna na stronę A4.",
    e_col_id: "ID", e_col_name: "Imię i nazwisko",
    e_saved: "Zapisano:",
    e_copy_made: "Utworzono kopię:",
    e_deleted: "Usunięto",
    e_roster_saved: "Zapisano listę uczniów",
    e_add_students_first: "Najpierw dodaj uczniów",
    e_generating_pdf: "Generuję PDF z kartami…",
    e_confirm_delete: "Usunąć quiz {name}?",
    e_imported: "Wczytano quiz z pliku",
    e_import_failed: "Nie udało się wczytać pliku — czy to plik quizu?",

    // ustawienia quizu
    s_quiz_settings: "Ustawienia quizu",
    s_default_time: "Domyślny czas pytania (s)",
    s_default_points: "Domyślne punkty",
    s_apply_all: "Zastosuj do wszystkich pytań",
    s_shuffle_q: "Losowa kolejność pytań",
    s_shuffle_a: "Losowa kolejność odpowiedzi",
    s_show_dist: "Pokaż rozkład odpowiedzi przy wyniku",
    s_auto_reveal_s: "Auto: ile pokazywać wynik (s)",
    s_auto_gap_s: "Auto: przerwa przed pytaniem (s)",
    s_applied: "Zastosowano do wszystkich pytań",
    s_app_settings: "Ustawienia aplikacji",
  },

  en: {
    app_name: "QuizScanner",
    lang_label: "Language",
    yes: "Yes", no: "No",
    save: "Save", cancel: "Cancel", delete: "Delete", close: "Close",

    t_load: "Load",
    t_editor: "✏️ Editor",
    t_board: "📺 Board",
    t_export: "⬇ Export results",
    t_no_quizzes: "— no quizzes, use the editor —",
    t_lan_board: "Board on network",
    t_cam_title: "Camera preview (scanner)",
    t_cam_hint: "Students turn their chosen letter to the top.",
    t_cam_wait: "⏳ Camera is starting or unavailable (check the source).",
    t_cam_source: "Video source",
    t_cam_apply: "Switch",
    t_cam_source_hint: "Camera number (0, 1, 2…) or a phone address, e.g. http://192.168.1.50:8080/video",
    t_phone_help: "📱 How to connect a phone?",
    t_question_of: "Question {n} / {total}",
    t_start: "▶ Start question",
    t_reveal: "✓ Show result",
    t_prev: "◀ Previous",
    t_next: "Next ▶",
    t_reset: "⟲ Reset points",
    t_stat_time: "Time",
    t_stat_answered: "Answered",
    t_stat_dist: "A/B/C/D",
    t_speed_label: "Points for speed",
    t_speed_sub: "Off = every correct answer is worth the same. On = faster earns more.",
    t_auto_label: "Automatic mode",
    t_auto_sub: "After the start the quiz reveals results and advances on its own — no clicking.",
    t_auto_running: "Automatic mode is running — the quiz drives itself.",
    t_students_live: "Live student answers",
    t_col_id: "ID", t_col_student: "Student", t_col_answer: "Answer", t_col_points: "Points",
    t_no_answers: "No answers yet",
    t_ranking: "Leaderboard",
    t_no_results: "No results",
    t_load_quiz_first: "Load a quiz to begin.",
    t_confirm_reset: "Reset all points and start over?",
    t_saved_results: "Results saved:",
    t_only_known: "Only students on the list",
    t_only_known_sub: "Ignores codes outside the list — protects against accidental detections in the background.",

    b_question_of: "Question {n} of {total}",
    b_scanned: "Scanned:",
    b_correct: "Correct:",
    b_prepare: "Get your card ready — turn your letter (A/B/C/D) to the top",
    b_ready: "Ready to start",
    b_load_hint: "Load a quiz in the teacher panel",
    b_end_kicker: "Quiz finished",
    b_standings: "Final standings",
    b_no_results: "No results",

    e_title: "QuizScanner · Editor",
    e_tab_quiz: "Quizzes",
    e_tab_roster: "Students",
    e_tab_settings: "Settings",
    e_to_teacher: "← Teacher panel",
    e_quizzes: "Quizzes",
    e_new_quiz: "+ New quiz",
    e_no_quizzes: "No quizzes — create one",
    e_quiz_title: "Quiz title",
    e_quiz_title_ph: "e.g. History revision",
    e_save: "💾 Save",
    e_duplicate: "⧉ Duplicate",
    e_delete: "🗑 Delete",
    e_export_file: "⬇ Save to file",
    e_import_file: "⬆ Load from file",
    e_file_hint: "You can send a .quiz file to another teacher.",
    e_editing_file: "file:",
    e_unsaved: "(new, unsaved)",
    e_question_n: "Question {n}",
    e_question_ph: "Question text…",
    e_answer_ph: "Answer {letter}",
    e_correct: "correct",
    e_time_s: "Time (s)",
    e_points: "Points (max)",
    e_add_question: "+ Add question",
    e_media: "Image / video",
    e_media_add: "🖼 Add file",
    e_media_remove: "✕ Remove file",
    e_media_hint: "Image (JPG/PNG/GIF/WEBP) or video (MP4/WEBM) — shown on the board with the question.",
    e_media_too_big: "File is too large (limit {mb} MB).",
    e_media_bad_type: "Unsupported file type.",
    e_roster_hint: "ID = marker number on the printed card.",
    e_save_roster: "💾 Save list",
    e_add_student: "+ Add student",
    e_cards_pdf: "📄 Download cards (PDF)",
    e_cards_hint: "Printable cards for the list above — one per A4 page.",
    e_col_id: "ID", e_col_name: "Full name",
    e_saved: "Saved:",
    e_copy_made: "Copy created:",
    e_deleted: "Deleted",
    e_roster_saved: "Student list saved",
    e_add_students_first: "Add students first",
    e_generating_pdf: "Generating cards PDF…",
    e_confirm_delete: "Delete quiz {name}?",
    e_imported: "Quiz loaded from file",
    e_import_failed: "Could not read the file — is it a quiz file?",

    s_quiz_settings: "Quiz settings",
    s_default_time: "Default question time (s)",
    s_default_points: "Default points",
    s_apply_all: "Apply to all questions",
    s_shuffle_q: "Shuffle question order",
    s_shuffle_a: "Shuffle answer order",
    s_show_dist: "Show answer distribution on reveal",
    s_auto_reveal_s: "Auto: result display time (s)",
    s_auto_gap_s: "Auto: pause before next question (s)",
    s_applied: "Applied to all questions",
    s_app_settings: "Application settings",
  },
};

let LANG = "pl";

function t(key, vars) {
  const table = I18N[LANG] || I18N.pl;
  let s = table[key];
  if (s === undefined) s = (I18N.pl[key] !== undefined ? I18N.pl[key] : key);
  if (vars) for (const k in vars) s = s.replaceAll("{" + k + "}", vars[k]);
  return s;
}

function setLang(lang) {
  LANG = I18N[lang] ? lang : "pl";
  document.documentElement.lang = LANG;
  applyI18n();
}

// Podmienia teksty w elementach oznaczonych atrybutami data-i18n*.
function applyI18n(root) {
  (root || document).querySelectorAll("[data-i18n]").forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  (root || document).querySelectorAll("[data-i18n-ph]").forEach(el => {
    el.placeholder = t(el.dataset.i18nPh);
  });
  (root || document).querySelectorAll("[data-i18n-title]").forEach(el => {
    el.title = t(el.dataset.i18nTitle);
  });
  document.dispatchEvent(new CustomEvent("i18n:changed"));
}

// Pobiera jezyk z serwera (wspolny dla panelu i tablicy) i stosuje go.
async function initLang() {
  try {
    const s = await (await fetch("/api/settings")).json();
    setLang(s.lang || "pl");
  } catch (e) { setLang("pl"); }
}
