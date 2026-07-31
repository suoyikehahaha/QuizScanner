// Edytor quizow i listy uczniow.
const LETTERS = ["A", "B", "C", "D"];
const $ = id => document.getElementById(id);

let quiz = { title: "", questions: [] };
let currentName = null;

function esc(s) {
  return (s || "").replace(/[&<>"]/g, c => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
function toast(msg) {
  const t = $("toast"); t.textContent = msg; t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 1600);
}
async function api(path, body) {
  const opt = body ? { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body) } : {};
  return (await fetch(path, opt)).json();
}

// ---------- lista quizow ----------
async function loadQuizList() {
  const r = await api("/api/quizzes");
  const ul = $("quizList"); ul.innerHTML = "";
  (r.quizzes || []).forEach(name => {
    const li = document.createElement("li");
    li.textContent = name;
    if (name === currentName) li.classList.add("active");
    li.onclick = () => selectQuiz(name);
    ul.appendChild(li);
  });
  if (!r.quizzes || !r.quizzes.length)
    ul.innerHTML = '<li class="muted">Brak quizów — utwórz nowy</li>';
}

async function selectQuiz(name) {
  const q = await api("/api/quiz?name=" + encodeURIComponent(name));
  quiz = normalize(q);
  currentName = name;
  renderAll();
}

function normalize(q) {
  q = q || {};
  return {
    title: q.title || "",
    questions: (q.questions || []).map(x => ({
      text: x.text || "",
      answers: [0, 1, 2, 3].map(i => (x.answers && x.answers[i]) || ""),
      correct: (typeof x.correct === "number") ? x.correct : 0,
      time: x.time || 20,
      points: x.points || 1000,
    })),
  };
}

// ---------- render pytan ----------
function renderAll() {
  $("quizTitle").value = quiz.title;
  $("editingName").textContent = currentName ? "plik: " + currentName : "(nowy, niezapisany)";
  renderQuestions();
  loadQuizList();
}

function renderQuestions() {
  const box = $("questions"); box.innerHTML = "";
  quiz.questions.forEach((q, qi) => {
    const card = document.createElement("div");
    card.className = "qcard";
    card.innerHTML = `
      <div class="qrow">
        <span class="qnum">Pytanie ${qi + 1}</span>
        <div class="qtools">
          <button class="btn-ghost" data-act="up" data-qi="${qi}">▲</button>
          <button class="btn-ghost" data-act="down" data-qi="${qi}">▼</button>
          <button class="btn-danger" data-act="del" data-qi="${qi}">🗑</button>
        </div>
      </div>
      <textarea class="text q-text" data-qi="${qi}" placeholder="Treść pytania…">${esc(q.text)}</textarea>
      <div class="opts-ed">
        ${[0, 1, 2, 3].map(ai => `
          <div class="opt-ed opt-${LETTERS[ai]}">
            <span class="badge">${LETTERS[ai]}</span>
            <input class="text q-ans" data-qi="${qi}" data-ai="${ai}"
                   placeholder="Odpowiedź ${LETTERS[ai]}" value="${esc(q.answers[ai])}">
            <label class="pick"><input type="radio" name="correct-${qi}" value="${ai}"
                   ${q.correct === ai ? "checked" : ""}> poprawna</label>
          </div>`).join("")}
      </div>
      <div class="meta-row">
        <div class="m"><label class="field">Czas (s)</label>
          <input class="text q-time" type="number" min="0" data-qi="${qi}" value="${q.time}"></div>
        <div class="m"><label class="field">Punkty (maks)</label>
          <input class="text q-points" type="number" min="0" step="100" data-qi="${qi}" value="${q.points}"></div>
      </div>`;
    box.appendChild(card);
  });

  // akcje strukturalne
  box.querySelectorAll("button[data-act]").forEach(b => {
    b.onclick = () => {
      syncFromDom();
      const qi = +b.dataset.qi;
      if (b.dataset.act === "del") quiz.questions.splice(qi, 1);
      if (b.dataset.act === "up" && qi > 0)
        [quiz.questions[qi - 1], quiz.questions[qi]] = [quiz.questions[qi], quiz.questions[qi - 1]];
      if (b.dataset.act === "down" && qi < quiz.questions.length - 1)
        [quiz.questions[qi + 1], quiz.questions[qi]] = [quiz.questions[qi], quiz.questions[qi + 1]];
      renderQuestions();
    };
  });
}

function syncFromDom() {
  quiz.title = $("quizTitle").value;
  document.querySelectorAll(".q-text").forEach(el => quiz.questions[+el.dataset.qi].text = el.value);
  document.querySelectorAll(".q-ans").forEach(el => quiz.questions[+el.dataset.qi].answers[+el.dataset.ai] = el.value);
  document.querySelectorAll(".q-time").forEach(el => quiz.questions[+el.dataset.qi].time = +el.value || 0);
  document.querySelectorAll(".q-points").forEach(el => quiz.questions[+el.dataset.qi].points = +el.value || 0);
  document.querySelectorAll('input[type=radio]:checked').forEach(el => {
    const qi = +el.name.split("-")[1]; quiz.questions[qi].correct = +el.value;
  });
}

// ---------- akcje quizu ----------
$("addQ").onclick = () => {
  syncFromDom();
  quiz.questions.push({ text: "", answers: ["", "", "", ""], correct: 0, time: 20, points: 1000 });
  renderQuestions();
};
$("newQuiz").onclick = () => {
  quiz = { title: "Nowy quiz", questions: [] };
  currentName = null; renderAll();
};
$("saveQuiz").onclick = async () => {
  syncFromDom();
  const name = currentName || (quiz.title || "quiz");
  const r = await api("/api/quiz", { name, quiz });
  currentName = r.name; renderAll(); toast("Zapisano: " + r.name);
};
$("dupQuiz").onclick = async () => {
  syncFromDom();
  const r = await api("/api/quiz", { name: (quiz.title || "quiz") + " kopia", quiz });
  currentName = r.name; renderAll(); toast("Utworzono kopię: " + r.name);
};
$("delQuiz").onclick = async () => {
  if (!currentName) { quiz = { title: "", questions: [] }; renderAll(); return; }
  if (!confirm("Usunąć quiz " + currentName + "?")) return;
  await api("/api/quiz/delete", { name: currentName });
  currentName = null; quiz = { title: "", questions: [] }; renderAll(); toast("Usunięto");
};
$("toTeacher").onclick = () => location.href = "/teacher";

// ---------- zakladki ----------
$("tabQuiz").onclick = () => switchTab("quiz");
$("tabRoster").onclick = () => switchTab("roster");
function switchTab(t) {
  $("tabQuiz").classList.toggle("active", t === "quiz");
  $("tabRoster").classList.toggle("active", t === "roster");
  $("quizView").classList.toggle("hidden", t !== "quiz");
  $("rosterView").classList.toggle("hidden", t !== "roster");
  if (t === "roster") loadRoster();
}

// ---------- roster ----------
let roster = {};
async function loadRoster() {
  roster = await api("/api/roster");
  renderRoster();
}
function renderRoster() {
  const body = $("rosterBody"); body.innerHTML = "";
  Object.keys(roster).map(Number).sort((a, b) => a - b).forEach(id => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input class="text r-id" type="number" value="${id}" style="width:70px"></td>
      <td><input class="text r-name" value="${esc(roster[id])}"></td>
      <td><button class="btn-danger r-del">✕</button></td>`;
    tr.querySelector(".r-del").onclick = () => { syncRoster(); delete roster[id]; renderRoster(); };
    body.appendChild(tr);
  });
}
function syncRoster() {
  const next = {};
  document.querySelectorAll("#rosterBody tr").forEach(tr => {
    const id = tr.querySelector(".r-id").value;
    const name = tr.querySelector(".r-name").value;
    if (id !== "") next[+id] = name;
  });
  roster = next;
}
$("addStudent").onclick = () => {
  syncRoster();
  const nextId = Object.keys(roster).length ? Math.max(...Object.keys(roster).map(Number)) + 1 : 0;
  roster[nextId] = ""; renderRoster();
};
$("saveRoster").onclick = async () => {
  syncRoster();
  await api("/api/roster", roster); toast("Zapisano listę uczniów");
};

// ---------- start ----------
(async function init() {
  const r = await api("/api/quizzes");
  if (r.quizzes && r.quizzes.length) await selectQuiz(r.active || r.quizzes[0]);
  else { quiz = { title: "Nowy quiz", questions: [] }; renderAll(); }
})();
