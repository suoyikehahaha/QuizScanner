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
const ctl = (action, extra) => api("/api/control", Object.assign({ action }, extra || {}));

// ---- sterowanie quizem ----
$("startBtn").onclick = () => ctl("start");
$("revealBtn").onclick = () => ctl("reveal");
$("nextBtn").onclick = () => ctl("next");
$("prevBtn").onclick = () => ctl("prev");
$("resetBtn").onclick = () => { if (confirm(t("t_confirm_reset"))) ctl("reset"); };
$("speedToggle").onchange = () => ctl("speed_bonus", { value: $("speedToggle").checked });
$("autoToggle").onchange = () => ctl("auto_mode", { value: $("autoToggle").checked });
$("editorBtn").onclick = () => window.open("/editor", "_blank");
$("boardBtn").onclick = () => window.open("/board", "_blank");
$("exportBtn").onclick = async () => {
  const r = await api("/api/export", {});
  if (r.ok) alert(t("t_saved_results") + "\n" + r.path);
};
$("loadBtn").onclick = async () => {
  const name = $("quizSel").value;
  if (name) await api("/api/load", { name });
  refreshState();
};

// ---- ustawienia aplikacji ----
$("langSel").onchange = async () => {
  await api("/api/settings", { lang: $("langSel").value });
  setLang($("langSel").value);
  refreshState();
};
$("onlyKnownToggle").onchange = () =>
  api("/api/settings", { only_known: $("onlyKnownToggle").checked });
$("camApply").onclick = async () => {
  await api("/api/settings", { camera: $("camSrc").value.trim() || "0" });
  // odśwież strumień podglądu (kamera startuje na nowo)
  setTimeout(() => { $("cam").src = "/video_feed?" + Date.now(); }, 800);
};

// ---- pomoc: telefon jako kamera ----
const PHONE_HELP = {
  pl: {
    title: "Telefon zamiast kamery internetowej",
    body: `
      <ol>
        <li>Zainstaluj w telefonie darmową aplikację streamującą obraz:
          <b>IP Webcam</b> (Android) albo <b>Iriun Webcam</b> / <b>DroidCam</b> (Android i iPhone).</li>
        <li>Podłącz telefon do <b>tej samej sieci Wi-Fi</b> co komputer.</li>
        <li>Uruchom aplikację i wybierz „Start server". Pokaże adres, np.
          <code>http://192.168.1.50:8080</code>.</li>
        <li>Wpisz tutaj adres strumienia i kliknij <b>Przełącz</b>:
          <ul>
            <li>IP Webcam: <code>http://192.168.1.50:8080/video</code></li>
            <li>DroidCam: <code>http://192.168.1.50:4747/video</code></li>
          </ul></li>
        <li>Ustaw telefon tak, by widział całą klasę — najlepiej na statywie
          lub oparty o coś stabilnego.</li>
      </ol>
      <p><b>Wskazówka:</b> Iriun i DroidCam mają też wersję na komputer, która
      tworzy zwykłą „kamerę” w systemie — wtedy zamiast adresu wpisz numer
      <code>1</code> lub <code>2</code>.</p>`,
  },
  en: {
    title: "Phone instead of a webcam",
    body: `
      <ol>
        <li>Install a free streaming app on the phone: <b>IP Webcam</b> (Android)
          or <b>Iriun Webcam</b> / <b>DroidCam</b> (Android and iPhone).</li>
        <li>Connect the phone to the <b>same Wi-Fi network</b> as the computer.</li>
        <li>Open the app and tap “Start server”. It shows an address, e.g.
          <code>http://192.168.1.50:8080</code>.</li>
        <li>Type the stream address here and click <b>Switch</b>:
          <ul>
            <li>IP Webcam: <code>http://192.168.1.50:8080/video</code></li>
            <li>DroidCam: <code>http://192.168.1.50:4747/video</code></li>
          </ul></li>
        <li>Position the phone so it sees the whole class — a tripod or a stable
          support works best.</li>
      </ol>
      <p><b>Tip:</b> Iriun and DroidCam also have desktop clients that create a
      regular system camera — then enter <code>1</code> or <code>2</code> instead
      of an address.</p>`,
  },
};
function showPhoneHelp() {
  const h = PHONE_HELP[document.documentElement.lang] || PHONE_HELP.pl;
  $("phTitle").textContent = h.title;
  $("phBody").innerHTML = h.body;
  $("phoneModal").classList.remove("hidden");
}
$("phoneHelpBtn").onclick = showPhoneHelp;
$("phClose").onclick = () => $("phoneModal").classList.add("hidden");
$("phoneModal").onclick = e => {
  if (e.target === $("phoneModal")) $("phoneModal").classList.add("hidden");
};

// ---- dane startowe ----
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
    sel.innerHTML = `<option value="">${t("t_no_quizzes")}</option>`;
}

async function loadMeta() {
  const m = await api("/api/meta");
  $("lanUrl").innerHTML = `${t("t_lan_board")}: <b>http://${m.lan_ip}:${m.port}/board</b>`;
}

async function loadSettings() {
  const s = await api("/api/settings");
  $("langSel").value = s.lang || "pl";
  $("camSrc").value = s.camera != null ? s.camera : "0";
  $("onlyKnownToggle").checked = !!s.only_known;
}

// ---- render ----
function updateCamNote(cameraOk) {
  const el = $("camNote");
  el.textContent = cameraOk ? t("t_cam_hint") : t("t_cam_wait");
  el.style.color = cameraOk ? "" : "var(--bad)";
}

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
    : `<tr><td colspan="4" style="color:var(--muted)">${t("t_no_answers")}</td></tr>`;
}

function renderLead(st) {
  const lead = st.leaderboard || [];
  $("lead").innerHTML = lead.length ? lead.map((r, i) =>
    `<li><span class="p">${i + 1}</span><span class="n">${esc(r.name)}</span><span class="s">${r.score} pkt</span></li>`
  ).join("") : `<li><span class="n" style="color:var(--muted)">${t("t_no_results")}</span></li>`;
}

const PHASE_KEY = { idle: "idle", question: "question", reveal: "reveal", podium: "podium" };

async function refreshState() {
  let st;
  try { st = await api("/api/state?full=1"); } catch (e) { return; }
  const q = st.question;
  $("counter").textContent = st.total
    ? t("t_question_of", { n: st.index + 1, total: st.total }) : "—";
  const ph = $("phase");
  ph.textContent = st.phase;
  ph.className = "phase " + (PHASE_KEY[st.phase] || "idle");
  $("qtext").textContent = q ? q.text : t("t_load_quiz_first");
  $("timeLeft").textContent = st.time_left != null ? Math.ceil(st.time_left) + " s" : "—";
  $("answered").textContent = st.answered;
  const d = st.distribution;
  $("dist").textContent = `${d.A}/${d.B}/${d.C}/${d.D}`;

  if (document.activeElement !== $("speedToggle")) $("speedToggle").checked = !!st.speed_bonus;
  if (document.activeElement !== $("autoToggle")) $("autoToggle").checked = !!st.auto_mode;
  if (document.activeElement !== $("onlyKnownToggle") && st.only_known != null)
    $("onlyKnownToggle").checked = !!st.only_known;

  // Pasek trybu automatycznego + blokada przycisków ręcznych.
  const bar = $("autoBar");
  if (st.auto_mode) {
    bar.classList.remove("hidden");
    bar.textContent = t("t_auto_running") +
      (st.auto_next_in != null ? "  ·  " + Math.ceil(st.auto_next_in) + " s" : "");
  } else {
    bar.classList.add("hidden");
  }
  ["startBtn", "revealBtn", "nextBtn", "prevBtn"].forEach(
    id => { $(id).disabled = !!st.auto_mode; });

  renderOpts(st);
  renderStudents(st);
  renderLead(st);
  updateCamNote(st.camera_ok);
}

// Po zmianie języka odśwież teksty zależne od danych.
document.addEventListener("i18n:changed", () => { loadQuizList(); loadMeta(); });

(async function init() {
  await initLang();
  await loadSettings();
  $("langSel").value = document.documentElement.lang;
  loadQuizList();
  loadMeta();
  refreshState();
  setInterval(refreshState, 500);
})();
