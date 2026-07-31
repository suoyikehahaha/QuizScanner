// Panel nauczyciela. Odpytuje /api/state?full=1 i steruje sesja.
const LETTERS = ["A", "B", "C", "D"];
const $ = id => document.getElementById(id);

function esc(s) {
  return (s || "").replace(/[&<>"]/g, c => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
async function api(path, body) {
  const opt = body ? { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body) } : {};
  return (await fetch(path, opt)).json();
}

// ---- sterowanie ----
$("startBtn").onclick = () => api("/api/control", { action: "start" });
$("revealBtn").onclick = () => api("/api/control", { action: "reveal" });
$("nextBtn").onclick = () => api("/api/control", { action: "next" });
$("prevBtn").onclick = () => api("/api/control", { action: "prev" });
$("resetBtn").onclick = () => { if (confirm("Wyzerować punkty i zacząć od nowa?")) api("/api/control", { action: "reset" }); };
$("speedToggle").onchange = () => api("/api/control", { action: "speed_bonus", value: $("speedToggle").checked });
$("editorBtn").onclick = () => window.open("/editor", "_blank");
$("boardBtn").onclick = () => window.open("/board", "_blank");
$("exportBtn").onclick = async () => {
  const r = await api("/api/export", {});
  if (r.ok) alert("Zapisano wyniki:\n" + r.path);
};
$("loadBtn").onclick = async () => {
  const name = $("quizSel").value;
  if (name) await api("/api/load", { name });
  refreshState();
};

async function loadQuizList() {
  const r = await api("/api/quizzes");
  const sel = $("quizSel");
  sel.innerHTML = "";
  (r.quizzes || []).forEach(q => {
    const o = document.createElement("option");
    o.value = q; o.textContent = q;
    if (q === r.active) o.selected = true;
    sel.appendChild(o);
  });
  if (!r.quizzes || !r.quizzes.length)
    sel.innerHTML = '<option value="">— brak quizów, użyj edytora —</option>';
}

async function loadMeta() {
  const m = await api("/api/meta");
  $("lanUrl").innerHTML = `Tablica w sieci: <b>http://${m.lan_ip}:${m.port}/board</b>`;
}

function updateCamNote(cameraOk) {
  const el = $("camNote");
  if (cameraOk) {
    el.textContent = "Uczniowie obracają kartę wybraną literą do góry.";
    el.style.color = "";
  } else {
    el.textContent = "⏳ Kamera się uruchamia lub niedostępna (sprawdź --camera).";
    el.style.color = "var(--bad)";
  }
}

// ---- render ----
function renderOpts(st) {
  const q = st.question;
  if (!q) { $("opts").innerHTML = ""; return; }
  $("opts").innerHTML = [0, 1, 2, 3].map(i => {
    const L = LETTERS[i];
    const correct = q.correct === i;
    return `<div class="opt-t opt-${L} ${correct ? "correct" : ""}">
      <span class="badge">${L}</span>
      <span class="c">${esc(q.answers[i] || "")}</span>
      <span class="num">${st.distribution[L] || 0}</span>
      ${correct ? '<span class="flag">✓</span>' : ""}
    </div>`;
  }).join("");
}

function renderStudents(st) {
  const students = st.students || {};
  const q = st.question || {};
  const correctL = (q.correct != null) ? LETTERS[q.correct] : null;
  const scores = st.scores || {};
  const rows = Object.keys(students).map(id => {
    const s = students[id];
    const ok = correctL && s.answer === correctL;
    const mark = correctL ? (ok ? '<span class="ans-ok">✓</span>' : '<span class="ans-bad">✗</span>') : "";
    return `<tr>
      <td>#${id}</td><td>${esc(s.name)}</td>
      <td><span class="badge badge-sm badge-${s.answer}">${s.answer}</span> ${mark}</td>
      <td>${scores[id] || 0}</td></tr>`;
  });
  $("studentsBody").innerHTML = rows.length ? rows.join("")
    : '<tr><td colspan="4" style="color:var(--muted)">Brak odpowiedzi</td></tr>';
}

function renderLead(st) {
  const lead = st.leaderboard || [];
  $("lead").innerHTML = lead.length ? lead.map((r, i) =>
    `<li><span class="p">${i + 1}</span><span class="n">${esc(r.name)}</span><span class="s">${r.score} pkt</span></li>`
  ).join("") : '<li><span class="n" style="color:var(--muted)">Brak wyników</span></li>';
}

async function refreshState() {
  let st;
  try { st = await api("/api/state?full=1"); } catch (e) { return; }
  const q = st.question;
  $("counter").textContent = st.total ? `Pytanie ${st.index + 1} / ${st.total}` : "—";
  const ph = $("phase");
  ph.textContent = st.phase;
  ph.className = "phase " + st.phase;
  $("qtext").textContent = q ? q.text : "Wczytaj quiz, aby rozpocząć.";
  $("timeLeft").textContent = st.time_left != null ? Math.ceil(st.time_left) + " s" : "—";
  $("answered").textContent = st.answered;
  const d = st.distribution;
  $("dist").textContent = `${d.A}/${d.B}/${d.C}/${d.D}`;
  if (document.activeElement !== $("speedToggle"))
    $("speedToggle").checked = !!st.speed_bonus;
  renderOpts(st);
  renderStudents(st);
  renderLead(st);
  updateCamNote(st.camera_ok);
}

loadQuizList();
loadMeta();
refreshState();
setInterval(refreshState, 500);
