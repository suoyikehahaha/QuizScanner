const previewKey = new URLSearchParams(location.search).get("preview");
let previewState = null;
if (previewKey && previewKey.startsWith("quizscanner.preview.")) {
  try { previewState = JSON.parse(sessionStorage.getItem(previewKey)); } catch {}
}
// Widok tablicy (rzutnik). Odpytuje /api/state i renderuje fazę.
const LETTERS = ["A", "B", "C", "D"];
const root = document.getElementById("root");
let last = "";
let currentState = null;
let boardControlBusy = false;

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

function boardNavigation(st) {
  if (previewState) return `<span>大屏预览 · 不控制课堂</span>`;
  if (!st.total) return "";
  const blocked = !!st.auto_mode || boardControlBusy;
  return `<div class="board-nav-controls" aria-label="题目导航">
    <button type="button" data-board-control="prev" ${blocked || st.index <= 0 ? "disabled" : ""}>
      <span aria-hidden="true">‹</span>${t("b_previous")}</button>
    <button type="button" data-board-control="next" ${blocked || st.phase === "podium" ? "disabled" : ""}>
      ${t("b_next")}<span aria-hidden="true">›</span></button>
    <span id="boardControlStatus" class="board-control-status" role="status" aria-live="polite"></span>
  </div>`;
}

async function sendBoardControl(action, extra = {}) {
  const response = await fetch("/api/control", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, expected_attempt: currentState?.attempt_id, command_id: String(Date.now()) + Math.random(), ...extra }),
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) throw new Error(data.error || `HTTP ${response.status}`);
  return data.state;
}

async function moveBoardQuestion(action) {
  if (boardControlBusy || !currentState?.total || currentState.auto_mode) return;
  const initial = currentState;
  boardControlBusy = true;
  root.querySelectorAll("[data-board-control]").forEach(button => { button.disabled = true; });
  const status = root.querySelector("#boardControlStatus");
  if (status) status.textContent = "正在切换…";
  try {
    const moved = await sendBoardControl(action + "_start");
    currentState = moved || initial;
    last = "";
    await tick();
  } catch (error) {
    const message = root.querySelector("#boardControlStatus");
    if (message) message.textContent = `切题失败：${error.message}`;
  } finally {
    boardControlBusy = false;
    root.querySelectorAll("[data-board-control]").forEach(button => {
      button.disabled = !!currentState?.auto_mode
        || (button.dataset.boardControl === "prev" && currentState?.index <= 0);
    });
  }
}

root.addEventListener("click", event => {
  if (event.target.closest(".material-open")) {
    const dialog = document.createElement("dialog");
    dialog.className = "material-dialog";
    dialog.innerHTML = `<button class="btn-primary material-close">返回题目</button><article>${tex(currentState?.question?.material || previewState?.question?.material || "")}</article>`;
    document.body.appendChild(dialog); dialog.showModal();
    dialog.querySelector("button").onclick = () => { dialog.close(); dialog.remove(); };
    return;
  }
  const button = event.target.closest("[data-board-control]");
  if (button && !button.disabled) moveBoardQuestion(button.dataset.boardControl);
  if (event.target.closest("[data-board-retry]")) tick();
});

function renderBoardConnectionError() {
  return `<main class="board-connection-error" role="alert">
    <div class="board-error-mark" aria-hidden="true">!</div>
    <h1>投影大屏暂时无法连接电脑</h1>
    <p>请确认电脑上的 QuizScanner 服务正在运行，并从电脑教师启动窗口重新打开“投影大屏”。</p>
    <p class="board-error-address">电脑本机通常使用 <b>http://localhost:8012/board</b>；其他设备请使用电脑显示的局域网地址和端口。</p>
    <button type="button" data-board-retry>重新连接</button>
  </main>`;
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
  const showDist = st.phase === "ended" || (reveal && st.show_distribution !== false);
  const count = st.distribution[LETTERS[i]] || 0;
  const maxCount = Math.max(1, ...Object.values(st.distribution));
  const barW = showDist ? Math.round(100 * count / maxCount) : 0;
  return `<div class="opt opt-${LETTERS[i]} ${isCorrect ? "correct" : ""} ${dim ? "dim" : ""}">
    <span class="badge">${LETTERS[i]}</span>
    <span class="txt">${tex(text)}</span>
    <span class="check">✓</span>
    ${showDist ? `<span class="count">${count}</span><span class="dist" style="width:${barW}%"></span>` : ""}
  </div>`;
}

function renderQuestion(st) {
  const q = st.question;
  const slide = q.slide || {};
  const savedTheme = slide.theme === "chinese-red" ? "chinese-paper" : slide.theme;
  const theme = ["night", "blue", "light", "chinese-paper", "ink", "jade", "chalkboard"].includes(savedTheme) ? savedTheme : "light";
  const layout = ["grid", "list"].includes(slide.layout) ? slide.layout : "grid";
  const size = ["small", "normal", "large"].includes(slide.size) ? slide.size : "normal";
  const optionSize = ["small", "normal", "large"].includes(slide.option_size) ? slide.option_size : "large";
  const low = st.time_left != null && st.time_left <= 5;
  const barW = (st.time_left != null && q.time) ? Math.max(0, 100 * st.time_left / q.time) : 100;
  const tiles = [0, 1, 2, 3].map(i => optionTile(i, q.answers[i] || "", st)).join("");
  const hasMedia = q.media && q.media.file;
  return `<div class="board-wrap">
    <div class="board-top">
      <div class="board-title">${esc(st.quiz_title)}</div>
      ${boardNavigation(st)}
      ${pips(st.total, st.index)}
      <div class="time-chip ${low ? "low" : ""}">${st.time_left != null ? Math.ceil(st.time_left) + "s" : "—"}</div>
    </div>
    <div class="time-bar"><i style="width:${barW}%"></i></div>
    <div class="board-layout">
      <main class="slide-stage">
        <section class="board-slide" data-theme="${theme}" data-layout="${layout}" data-size="${size}" data-option-size="${optionSize}">
          <div class="ppt-kicker">${t("b_question_of", { n: st.index + 1, total: st.total })}</div>
          ${q.material ? `<button class="btn-ghost material-open" type="button">查看阅读材料</button>` : ""}
          <div class="ppt-question">${tex(q.text)}</div>
          ${hasMedia ? mediaBlock(q) : ""}
          <div class="answers ${hasMedia ? "compact" : ""}" data-layout="${layout}">${tiles}</div>
          <div class="ppt-instruction">${st.phase === "ended"
            ? "本题作答已结束" : st.phase === "reveal" && q.correct != null
              ? `${t("b_correct")} <b>${LETTERS[q.correct]}</b> · ${tex(q.answers[q.correct])}` : t("b_prepare")}</div>
        </section>
      </main>
      <aside class="live-side" id="liveSide">${renderLivePanel(st)}</aside>
    </div>
  </div>`;
}

function renderLivePanel(st) {
  const students = Array.isArray(st.live_students) ? st.live_students : [];
  const answered = students.filter(student => student.scanned || student.answer).length;
  const total = Math.max(Number(st.roster_total) || 0, students.length, answered);
  const counts = LETTERS.map(letter => Number(st.distribution?.[letter]) || 0);
  const maxCount = Math.max(1, ...counts);
  const showDistribution = st.phase !== "question" || st.scan_visibility !== "status";
  const distribution = showDistribution ? LETTERS.map((letter, i) => `
    <div class="live-dist-row"><b class="badge badge-${letter}">${letter}</b><i><span style="width:${Math.round(100 * counts[i] / maxCount)}%"></span></i><strong>${counts[i]}</strong></div>`).join("") : "";
  const rows = students.map(student => renderLiveStudent(student, st)).join("");
  const countText = t("b_answered_count", { answered, total });
  const progress = total ? Math.min(100, Math.round(100 * answered / total)) : 0;
  return `<div class="live-panel-head"><div><span class="live-eyebrow">${esc(st.active_class || "")}${st.active_class ? " · " : ""}${t("b_live_title")}</span><strong>${countText}</strong></div>
    <div class="live-progress"><i style="width:${progress}%"></i></div></div>
    ${showDistribution ? `<div class="live-distribution">${distribution}</div>` : ""}
    <ol class="live-students">${rows || `<li class="live-empty">${t("b_no_answers")}</li>`}</ol>`;
}

function liveStudentStatus(student, st) {
  const answer = LETTERS.includes(student.answer) ? student.answer : null;
  const revealed = st.phase === "reveal" && answer;
  const isCorrect = revealed && st.question && st.question.correct === LETTERS.indexOf(answer);
  if (answer) return {
    className: `live-answer ${revealed ? (isCorrect ? "is-correct" : "is-wrong") : ""}`.trim(),
    text: `${revealed ? (isCorrect ? "✓ " : "") : ""}${answer}`,
  };
  return student.scanned
    ? { className: "live-scanned", text: "已扫描" }
    : { className: "live-pending", text: t("b_waiting") };
}

function renderLiveStudent(student, st) {
  const status = liveStudentStatus(student, st);
  return `<li class="live-student ${student.scanned ? "has-answer" : ""}" data-student-key="${esc(student.id)}">
    <span class="live-name"><small>${esc(student.id)}</small><b>${esc(student.name || "")}</b></span>
    <span class="live-status ${status.className}">${esc(status.text)}</span></li>`;
}

function setTextNode(element, value) {
  if (element.firstChild && element.firstChild.nodeType === Node.TEXT_NODE
      && element.childNodes.length === 1) element.firstChild.nodeValue = value;
  else element.textContent = value;
}

function updateLiveStudent(existing, next, st) {
  existing.classList.toggle("has-answer", !!next.scanned);
  setTextNode(existing.querySelector(".live-name small"), String(next.id ?? ""));
  setTextNode(existing.querySelector(".live-name b"), String(next.name || ""));
  const status = liveStudentStatus(next, st);
  const statusNode = existing.querySelector(".live-status");
  statusNode.className = `live-status ${status.className}`;
  setTextNode(statusNode, status.text);
}

function updateLivePanel(st) {
  const side = root.querySelector("#liveSide");
  if (!side) return;
  const template = document.createElement("div");
  template.innerHTML = renderLivePanel(st);
  const nextHead = template.querySelector(".live-panel-head");
  const oldHead = side.querySelector(".live-panel-head");
  if (oldHead) oldHead.replaceWith(nextHead);
  const nextDistribution = template.querySelector(".live-distribution");
  const oldDistribution = side.querySelector(".live-distribution");
  const list = side.querySelector(".live-students");
  if (!list) return;
  if (nextDistribution && oldDistribution) oldDistribution.replaceWith(nextDistribution);
  else if (nextDistribution) side.insertBefore(nextDistribution, list);
  else if (oldDistribution) oldDistribution.remove();

  const nextRows = Array.from(template.querySelectorAll(".live-students > li"));
  const currentRows = Array.from(list.children);
  const sameOrder = currentRows.length === nextRows.length && currentRows.every((row, index) =>
    row.dataset.studentKey === nextRows[index].dataset.studentKey);
  if (!sameOrder) {
    list.replaceChildren(...nextRows);
    return;
  }
  studentsForRows(st, currentRows);
}

function studentsForRows(st, rows) {
  const students = Array.isArray(st.live_students) ? st.live_students : [];
  if (!students.length || (rows[0] && rows[0].classList.contains("live-empty"))) return;
  rows.forEach((row, index) => updateLiveStudent(row, students[index], st));
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
    ${boardNavigation(st)}
    <h1>${tex(st.question.text)}</h1>
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
    <div class="board-podium-nav">${boardNavigation(st)}</div>
    <div class="kicker">${t("b_end_kicker")}</div>
    <h1>${t("b_standings")}</h1>
    <div class="podium">${rows || `<div class="rank-row"><span class="who">${t("b_no_results")}</span></div>`}</div>
  </div>`;
}

function render(st) {
  if (st.phase === "podium") return renderPodium(st);
  if (st.phase === "question" || st.phase === "ended" || st.phase === "reveal") return renderQuestion(st);
  return renderIdle(st);
}

async function tick() {
  try {
    const st = previewState || await (await fetch("/api/state?live=1")).json();
    currentState = st;
    const key = document.documentElement.lang + st.phase + st.index + String(st.auto_mode) + JSON.stringify(st.question)
      + (st.phase === "podium" ? JSON.stringify(st.leaderboard) : "");
    if (key !== last) { root.innerHTML = render(st); last = key; }
    else {
      // 只更新倒计时和名单，避免学生每次提交答案都重启题目视频。
      const chip = root.querySelector(".time-chip");
      const bar = root.querySelector(".time-bar > i");
      if (chip && st.time_left != null && st.question) {
        chip.textContent = Math.ceil(st.time_left) + "s";
        chip.classList.toggle("low", st.time_left <= 5);
        if (bar) bar.style.width = Math.max(0, 100 * st.time_left / st.question.time) + "%";
      }
      if (root.querySelector("#liveSide")
          && (st.phase === "question" || st.phase === "ended" || st.phase === "reveal"))
        updateLivePanel(st);
    }
  } catch (e) {
    last = null;
    if (!root.querySelector(".board-connection-error")) root.innerHTML = renderBoardConnectionError();
  }
}

// Język, motyw i dźwięk zmienia się w panelu nauczyciela — tablica dopytuje,
// żeby ustawienia działały też na drugim komputerze przy rzutniku.
async function pollSettings() {
  try {
    applyServerSettings(await (await fetch("/api/presentation")).json());
  } catch (e) { }
}

(async function init() {
  await initLang();
  tick();
  if (!previewState) setInterval(tick, 350);
  if (!previewState) setInterval(pollSettings, 2000);
})();
