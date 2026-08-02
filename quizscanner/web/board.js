// Widok tablicy (rzutnik). Odpytuje /api/state i renderuje fazę.
const LETTERS = ["A", "B", "C", "D"];
const root = document.getElementById("root");
let last = "";

function esc(s) {
  return (s || "").replace(/[&<>"]/g, c => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function pips(total, index) {
  let out = "";
  for (let i = 0; i < total; i++) {
    const cls = i < index ? "done" : (i === index ? "cur" : "");
    out += `<span class="pip ${cls}"></span>`;
  }
  return `<div class="pips">${out}</div>`;
}

// Zdjęcie lub film dołączony do pytania.
function mediaBlock(q) {
  const m = q.media;
  if (!m || !m.file) return "";
  const src = "/media/" + encodeURIComponent(m.file);
  if (m.type === "video") {
    return `<div class="qmedia"><video src="${src}" autoplay muted loop playsinline></video></div>`;
  }
  return `<div class="qmedia"><img src="${src}" alt=""></div>`;
}

function optionTile(i, text, st) {
  const q = st.question;
  const reveal = st.phase === "reveal";
  const isCorrect = reveal && q.correct === i;
  const dim = reveal && q.correct != null && q.correct !== i;
  const showDist = reveal && st.show_distribution !== false;
  const count = st.distribution[LETTERS[i]] || 0;
  const maxCount = Math.max(1, ...Object.values(st.distribution));
  const barW = showDist ? Math.round(100 * count / maxCount) : 0;
  return `<div class="opt opt-${LETTERS[i]} ${isCorrect ? "correct" : ""} ${dim ? "dim" : ""}">
    <span class="badge">${LETTERS[i]}</span>
    <span class="txt">${esc(text)}</span>
    <span class="check">✓</span>
    ${showDist ? `<span class="count">${count}</span><span class="dist" style="width:${barW}%"></span>` : ""}
  </div>`;
}

function renderQuestion(st) {
  const q = st.question;
  const low = st.time_left != null && st.time_left <= 5;
  const barW = (st.time_left != null && q.time) ? Math.max(0, 100 * st.time_left / q.time) : 100;
  const tiles = [0, 1, 2, 3].map(i => optionTile(i, q.answers[i] || "", st)).join("");
  const hasMedia = q.media && q.media.file;
  return `<div class="board-wrap">
    <div class="board-top">
      <div class="board-title">${esc(st.quiz_title)}</div>
      ${pips(st.total, st.index)}
      <div class="time-chip ${low ? "low" : ""}">${st.time_left != null ? Math.ceil(st.time_left) + "s" : "—"}</div>
    </div>
    <div class="time-bar"><i style="width:${barW}%"></i></div>
    <div class="kicker">${t("b_question_of", { n: st.index + 1, total: st.total })}</div>
    <div class="qtext ${hasMedia ? "with-media" : ""}">${esc(q.text)}</div>
    ${mediaBlock(q)}
    <div class="answers ${hasMedia ? "compact" : ""}">${tiles}</div>
    <div class="board-foot">
      <span class="chip">◎ ${t("b_scanned")} <b>${st.answered}</b></span>
      ${st.phase === "reveal" && q.correct != null
        ? `<span class="chip">${t("b_correct")} <span class="badge badge-${LETTERS[q.correct]}">${LETTERS[q.correct]}</span> ${esc(q.answers[q.correct])}</span>` : ""}
    </div>
  </div>`;
}

function renderIdle(st) {
  if (!st.question) {
    return `<div class="center-screen">
      <img class="idle-logo" src="/static/logo.svg" alt="">
      <div class="kicker">QuizScanner</div>
      <h1>${esc(st.quiz_title || t("b_ready"))}</h1>
      <p>${t("b_load_hint")}</p>
      <div class="scanline"></div>
    </div>`;
  }
  return `<div class="center-screen">
    <div class="kicker">${t("b_question_of", { n: st.index + 1, total: st.total })}</div>
    <h1>${esc(st.question.text)}</h1>
    <div class="scanline"></div>
    <p>${t("b_prepare")}</p>
  </div>`;
}

function renderPodium(st) {
  const rows = st.leaderboard.map((r, i) => `
    <div class="rank-row ${i < 3 ? "top" + (i + 1) : ""}">
      <span class="pos">${i + 1}</span>
      <span class="who">${esc(r.name)}</span>
      <span class="pts">${r.score} pkt</span>
    </div>`).join("");
  return `<div class="center-screen">
    <div class="kicker">${t("b_end_kicker")}</div>
    <h1>${t("b_standings")}</h1>
    <div class="podium">${rows || `<div class="rank-row"><span class="who">${t("b_no_results")}</span></div>`}</div>
  </div>`;
}

function render(st) {
  if (st.phase === "podium") return renderPodium(st);
  if (st.phase === "question" || st.phase === "reveal") return renderQuestion(st);
  return renderIdle(st);
}

// ---- dźwięki ----
// Tablica reaguje na zmiany stanu, a nie na kliknięcia, więc sygnały
// wyzwalamy porównując kolejne odpowiedzi serwera.
let prev = { phase: null, index: null, sec: null };

function cues(st) {
  if (!Sound.enabled) return;
  const sec = st.time_left != null ? Math.ceil(st.time_left) : null;

  if (st.phase !== prev.phase || st.index !== prev.index) {
    if (st.phase === "question") Sound.play("start");
    else if (st.phase === "reveal") Sound.play("reveal");
    else if (st.phase === "podium") Sound.play("podium");
    else if (prev.phase === "reveal") Sound.play("next");
  } else if (st.phase === "question" && sec != null && sec !== prev.sec) {
    // Odliczanie: ostatnie pięć sekund, ostatnia wyraźnie wyżej.
    if (sec === 0) Sound.play("timeup");
    else if (sec <= 5) Sound.play(sec === 1 ? "tickLast" : "tick");
  }
  prev = { phase: st.phase, index: st.index, sec };
}

// Przeglądarka nie zagra nic, dopóki ktoś nie kliknie w stronę.
function soundGate() {
  const el = document.getElementById("soundGate");
  if (!el) return;
  el.classList.toggle("hidden", !Sound.blocked);
  el.textContent = t("b_sound_locked");
}
document.addEventListener("pointerdown", () => { Sound.unlock(); soundGate(); });
document.addEventListener("keydown", () => { Sound.unlock(); soundGate(); });

async function tick() {
  try {
    const st = await (await fetch("/api/state")).json();
    cues(st);
    const key = document.documentElement.lang + st.phase + st.index + st.answered
      + JSON.stringify(st.distribution)
      + (st.phase === "podium" ? JSON.stringify(st.leaderboard) : "");
    if (key !== last) { root.innerHTML = render(st); last = key; }
    else {
      // płynna aktualizacja samego timera bez przerysowania (nie przerywa filmu)
      const chip = root.querySelector(".time-chip");
      const bar = root.querySelector(".time-bar > i");
      if (chip && st.time_left != null && st.question) {
        chip.textContent = Math.ceil(st.time_left) + "s";
        chip.classList.toggle("low", st.time_left <= 5);
        if (bar) bar.style.width = Math.max(0, 100 * st.time_left / st.question.time) + "%";
      }
    }
  } catch (e) { /* serwer chwilowo niedostępny */ }
}

// Język, motyw i dźwięk zmienia się w panelu nauczyciela — tablica dopytuje,
// żeby ustawienia działały też na drugim komputerze przy rzutniku.
async function pollSettings() {
  try {
    applyServerSettings(await (await fetch("/api/settings")).json());
    soundGate();
  } catch (e) { }
}

(async function init() {
  await initLang();
  soundGate();
  tick();
  setInterval(tick, 350);
  setInterval(pollSettings, 2000);
})();
