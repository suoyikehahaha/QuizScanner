// Widok tablicy (rzutnik). Odpytuje /api/state i renderuje faze.
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

function optionTile(i, text, st) {
  const q = st.question;
  const reveal = st.phase === "reveal";
  const isCorrect = reveal && q.correct === i;
  const dim = reveal && q.correct != null && q.correct !== i;
  const count = st.distribution[LETTERS[i]] || 0;
  const maxCount = Math.max(1, ...Object.values(st.distribution));
  const barW = reveal ? Math.round(100 * count / maxCount) : 0;
  return `<div class="opt opt-${LETTERS[i]} ${isCorrect ? "correct" : ""} ${dim ? "dim" : ""}">
    <span class="badge">${LETTERS[i]}</span>
    <span class="txt">${esc(text)}</span>
    <span class="check">✓</span>
    ${reveal ? `<span class="count">${count}</span><span class="dist" style="width:${barW}%"></span>` : ""}
  </div>`;
}

function renderQuestion(st) {
  const q = st.question;
  const low = st.time_left != null && st.time_left <= 5;
  const barW = (st.time_left != null && q.time) ? Math.max(0, 100 * st.time_left / q.time) : 100;
  const tiles = [0, 1, 2, 3].map(i => optionTile(i, q.answers[i] || "", st)).join("");
  return `<div class="board-wrap">
    <div class="board-top">
      <div class="board-title">${esc(st.quiz_title)}</div>
      ${pips(st.total, st.index)}
      <div class="time-chip ${low ? "low" : ""}">${st.time_left != null ? Math.ceil(st.time_left) + "s" : "—"}</div>
    </div>
    <div class="time-bar"><i style="width:${barW}%"></i></div>
    <div class="kicker">Pytanie ${st.index + 1} z ${st.total}</div>
    <div class="qtext">${esc(q.text)}</div>
    <div class="answers">${tiles}</div>
    <div class="board-foot">
      <span class="chip">◎ Zeskanowano: <b>${st.answered}</b></span>
      ${st.phase === "reveal" && q.correct != null
        ? `<span class="chip">Poprawna: <span class="badge badge-${LETTERS[q.correct]}">${LETTERS[q.correct]}</span> ${esc(q.answers[q.correct])}</span>` : ""}
    </div>
  </div>`;
}

function renderIdle(st) {
  if (!st.question) {
    return `<div class="center-screen">
      <img class="idle-logo" src="/static/logo.svg" alt="">
      <div class="kicker">QuizScanner</div>
      <h1>${esc(st.quiz_title || "Gotowi do startu")}</h1>
      <p>Wczytaj quiz w panelu nauczyciela</p>
      <div class="scanline"></div>
    </div>`;
  }
  return `<div class="center-screen">
    <div class="kicker">Pytanie ${st.index + 1} z ${st.total}</div>
    <h1>${esc(st.question.text)}</h1>
    <div class="scanline"></div>
    <p>Przygotuj kartę — obróć wybraną literę (A/B/C/D) do góry</p>
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
    <div class="kicker">Koniec quizu</div>
    <h1>Klasyfikacja</h1>
    <div class="podium">${rows || '<div class="rank-row"><span class="who">Brak wyników</span></div>'}</div>
  </div>`;
}

function render(st) {
  if (st.phase === "podium") return renderPodium(st);
  if (st.phase === "question" || st.phase === "reveal") return renderQuestion(st);
  return renderIdle(st);
}

async function tick() {
  try {
    const st = await (await fetch("/api/state")).json();
    const html = render(st);
    const key = st.phase + st.index + st.answered + JSON.stringify(st.distribution)
      + (st.phase === "podium" ? JSON.stringify(st.leaderboard) : "");
    if (key !== last) { root.innerHTML = html; last = key; }
    else {
      // plynna aktualizacja samego timera bez przerysowania
      const chip = root.querySelector(".time-chip");
      const bar = root.querySelector(".time-bar > i");
      if (chip && st.time_left != null && st.question) {
        chip.textContent = Math.ceil(st.time_left) + "s";
        chip.classList.toggle("low", st.time_left <= 5);
        if (bar) bar.style.width = Math.max(0, 100 * st.time_left / st.question.time) + "%";
      }
    }
  } catch (e) { /* serwer chwilowo niedostepny */ }
}

setInterval(tick, 350);
tick();
