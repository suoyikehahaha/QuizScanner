const $ = id => document.getElementById(id);
const LETTERS = ["A", "B", "C", "D"];
const MAX_DOCX_BYTES = 8 * 1024 * 1024;
const MAX_ROSTER_BYTES = 3 * 1024 * 1024;
const RECENT_QUIZZES_KEY = "quizscanner.recent-quizzes.v1";

async function api(path, body) {
  const options = { cache: "no-store" };
  if (body !== undefined) {
    options.method = "POST";
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  const data = await response.json();
  if (path === "/api/settings" && response.ok && data.settings) {
    cachedSettings = data.settings;
    settingsFetchedAt = Date.now();
  }
  if (!response.ok || data.ok === false) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}

const control = (action, extra = {}) => api("/api/control", { action, ...extra });
let state = null;
let busy = false;
let refreshing = false;
let settingsLoaded = false;
let cachedSettings = null;
let settingsFetchedAt = 0;
let mobileRefreshTimer = null;
let currentRoster = { version: 2, classes: [], active_class: "", students: [] };
let stagedRoster = null;
let stagedQuiz = null;
let toastTimer = null;
let scanVisible = false;
let scanDismissed = false;
let scanDrawerTab = "graph";
let scanDrawerOpen = false;
let observedPhase = null;
let observedQuestionIndex = null;
let scanPreviewHome = null;
let quizCatalog = { quizzes: [], active: null, details: [] };
let lastScanGraphSignature = null;
let lastScanStudentsSignature = null;
let mobileTransitionTimer = null;
let pageTouchStart = null;

function scheduleMobileRefresh() {
  if (mobileRefreshTimer !== null) clearInterval(mobileRefreshTimer);
  mobileRefreshTimer = setInterval(refresh, scanVisible ? 250 : 1500);
}

function nativeBridge() {
  return window.QuizScannerNative || null;
}

function setScanTab(tab, open = true) {
  scanDrawerTab = tab === "students" ? "students" : "graph";
  scanDrawerOpen = open;
  const experience = $("scanExperience");
  const drawer = $("scanDrawer");
  const graph = scanDrawerTab === "graph";
  $("scanGraphPanel").classList.toggle("hidden", !graph);
  $("scanStudentsPanel").classList.toggle("hidden", graph);
  $("scanGraphTab").classList.toggle("active", open && graph);
  $("scanStudentsTab").classList.toggle("active", open && !graph);
  $("scanGraphTab").setAttribute("aria-pressed", String(open && graph));
  $("scanStudentsTab").setAttribute("aria-pressed", String(open && !graph));
  experience.classList.toggle("drawer-closed", !open);
  drawer.classList.toggle("collapsed", !open);
  $("scanDrawerTitle").textContent = graph ? "选项分布" : "学生作答状态";
  if (state) graph ? renderScanGraph(state) : renderScanStudents(state);
}

function enterScanExperience(startCamera = false) {
  if (scanVisible) {
    if (startCamera) nativeBridge()?.startCamera();
    return;
  }
  scanVisible = true;
  scanDismissed = false;
  scheduleMobileRefresh();
  const experience = $("scanExperience");
  const preview = $("scanPreview");
  if (preview && !scanPreviewHome) scanPreviewHome = preview.parentElement;
  if (preview) $("scanCameraStage").appendChild(preview);
  experience.classList.remove("hidden");
  experience.setAttribute("aria-hidden", "false");
  document.body.classList.add("scan-open");
  setScanTab("graph", false);
  if (nativeBridge()?.enterScanMode) {
    nativeBridge().enterScanMode();
  } else if (experience.requestFullscreen) {
    experience.requestFullscreen().catch(() => {});
  }
  if (startCamera) nativeBridge()?.startCamera();
  $("resumeScanButton").classList.add("hidden");
  $("scanCameraPrompt").classList.toggle("hidden", !!nativeBridge()?.isCameraRunning?.());
}

function exitScanExperience({ dismissed = false, notifyNative = true, fromFullscreen = false } = {}) {
  if (dismissed) scanDismissed = true;
  if (!scanVisible) {
    if (notifyNative) nativeBridge()?.exitScanMode();
    return;
  }
  scanVisible = false;
  scheduleMobileRefresh();
  const preview = $("scanPreview");
  if (preview && scanPreviewHome) scanPreviewHome.appendChild(preview);
  $("scanExperience").classList.add("hidden");
  $("scanExperience").setAttribute("aria-hidden", "true");
  document.body.classList.remove("scan-open");
  if (notifyNative) nativeBridge()?.exitScanMode();
  if (!fromFullscreen && document.fullscreenElement && document.exitFullscreen) {
    document.exitFullscreen().catch(() => {});
  }
  $("resumeScanButton").classList.toggle("hidden", !["question", "ended", "reveal"].includes(state?.phase));
}

window.exitScanExperienceFromNative = () => {
  exitScanExperience({ dismissed: true, notifyNative: false, fromFullscreen: true });
};

document.addEventListener("fullscreenchange", () => {
  if (!document.fullscreenElement && scanVisible && !nativeBridge()) {
    exitScanExperience({ dismissed: true, notifyNative: false, fromFullscreen: true });
  }
});

function observeScanPhase(data) {
  const active = ["question", "ended", "reveal"].includes(data.phase);
  const newQuestion = data.phase === "question" &&
    (observedPhase !== "question" || observedQuestionIndex !== data.attempt_id);
  if (newQuestion) {
    scanDismissed = false;
    if (scanVisible) setScanTab("graph", false);
    if (data.quiz_name) {
      rememberRecentQuiz(data.quiz_name);
      renderQuizCollections(quizCatalog);
    }
  }
  if (active && !scanDismissed) enterScanExperience(newQuestion);
  if (["ended", "reveal"].includes(data.phase) && observedPhase === "question") {
    nativeBridge()?.stopCamera?.();
    setScanTab("graph", true);
  }
  if (data.phase === "podium") exitScanExperience();
  if (data.phase === "idle" && ["question", "ended", "reveal"].includes(observedPhase)) {
    exitScanExperience();
  }
  observedPhase = data.phase;
  observedQuestionIndex = data.attempt_id;
  $("resumeScanButton").classList.toggle("hidden", !active || scanVisible);
}

function renderScanGraph(data) {
  const answers = data.question?.answers || [];
  const distribution = data.distribution || {};
  const counts = LETTERS.map(letter => Number(distribution[letter]) || 0);
  const signature = JSON.stringify([answers, counts]);
  if (signature === lastScanGraphSignature) return;
  lastScanGraphSignature = signature;
  const max = Math.max(1, ...counts);
  const box = $("scanGraphPanel");
  box.replaceChildren();
  LETTERS.forEach((letter, index) => {
    const row = document.createElement("div");
    row.className = "scan-graph-row";
    row.dataset.letter = letter;
    const badge = document.createElement("span");
    badge.className = "scan-graph-letter";
    badge.textContent = letter;
    const copy = document.createElement("span");
    copy.className = "scan-graph-copy";
    const text = document.createElement("strong");
    text.textContent = answers[index] || "（空选项）";
    const track = document.createElement("span");
    track.className = "scan-graph-track";
    const bar = document.createElement("i");
    bar.style.width = `${Math.round(100 * counts[index] / max)}%`;
    track.appendChild(bar);
    copy.append(text, track);
    const count = document.createElement("span");
    count.className = "scan-graph-count";
    count.textContent = String(counts[index]);
    row.append(badge, copy, count);
    box.appendChild(row);
  });
}

function renderScanStudents(data) {
  const students = Array.isArray(data.live_students) ? data.live_students : [];
  const signature = JSON.stringify(students.map(student => [student.id, student.scanned, student.answer, student.name]));
  if (signature === lastScanStudentsSignature) return;
  lastScanStudentsSignature = signature;
  const box = $("scanStudentsPanel");
  box.replaceChildren();
  if (!students.length) {
    const empty = document.createElement("div");
    empty.className = "scan-empty";
    empty.textContent = "当前班级暂无学生名单";
    box.appendChild(empty);
    return;
  }
  students.forEach(student => {
    const item = document.createElement("div");
    item.className = `scan-student${student.scanned ? " scanned" : ""}`;
    const dot = document.createElement("i");
    dot.className = "scan-student-dot";
    const label = document.createElement("span");
    label.className = "scan-student-label";
    label.textContent = String(student.name || "未命名学生");
    label.title = `${student.name || "未命名学生"} · ${student.student_no || student.id || ""}`;
    const answer = document.createElement("span");
    answer.className = `scan-student-answer${student.answer ? " has-answer" : ""}`;
    answer.textContent = student.answer || (student.scanned ? "已扫" : "");
    item.append(dot, label, answer);
    box.appendChild(item);
  });
}

function renderScanExperience(data, meta) {
  const students = Array.isArray(data.live_students) ? data.live_students : [];
  const scanned = students.filter(student => student.scanned).length;
  const total = Number(data.roster_total) || students.length;
  const answered = Number(data.answered) || scanned;
  $("scanAnswered").textContent = String(answered);
  $("scanTotal").textContent = String(total);
  $("scanClassName").textContent = data.active_class || "未选择班级";
  $("scanQuestionCounter").textContent = data.total
    ? `第 ${data.index + 1} 题 / 共 ${data.total} 题` : "尚未加载测验";
  $("scanQuestionText").textContent = data.question?.text || "等待题目";
  $("scanTimeLeft").textContent = data.time_left == null ? "不限时" : `${Math.ceil(data.time_left)} 秒`;
  $("scanTimeLeft").classList.toggle("low", data.time_left != null && data.time_left <= 5);
  $("scanDrawerCount").textContent = `${answered} 人已作答`;
  $("scanDrawerSubtitle").textContent = data.phase === "ended" ? "本题已结束" : "实时识别";
  $("scanDrawerTitle").textContent = scanDrawerTab === "graph" ? "选项分布" : "学生作答状态";
  if (document.activeElement !== $("scanShowAnswersToggle"))
    $("scanShowAnswersToggle").checked = data.show_student_answers_on_reveal !== false;
  if (scanDrawerTab === "graph") renderScanGraph(data);
  else renderScanStudents(data);
  const isQuestion = data.phase === "question";
  $("scanEndButton").disabled = !isQuestion || busy || !!data.auto_mode;
  $("scanEndButton").textContent = data.auto_mode ? "自动模式进行中" : isQuestion ? "结束作答" : "作答已结束";
  const last = data.total > 0 && data.index >= data.total - 1;
  $("scanNextButton").disabled = busy || !!data.auto_mode || !["question", "ended", "reveal"].includes(data.phase);
  $("scanNextButton").textContent = last ? "结束测验" : "下一题并开始";
  const running = !!nativeBridge()?.isCameraRunning?.();
  const canEndAnswer = isQuestion && !data.auto_mode;
  const canViewResults = ["ended", "reveal"].includes(data.phase);
  $("scanCameraButton").disabled = busy || (!canEndAnswer && !canViewResults);
  $("scanCameraButton").classList.toggle("answer-ended", canViewResults);
  $("scanCameraButton").setAttribute("aria-label", canEndAnswer
    ? "结束作答并查看选项统计" : canViewResults ? "显示选项统计" : "自动作答中" );
  $("scanCameraButton").title = canEndAnswer ? "结束作答并查看选项统计"
    : canViewResults ? "显示选项统计" : "自动作答中";
  $("scanCameraButton").dataset.cameraRunning = String(running);
  const androidCamera = !!nativeBridge();
  const cameraPaused = scanVisible && androidCamera && !running && ["ended", "reveal"].includes(data.phase);
  $("scanPreview").classList.toggle("camera-paused", cameraPaused);
  if (cameraPaused) {
    $("scanCameraPrompt").innerHTML = "摄像头已关闭<br><small>下一题开始时自动开启扫码</small>";
    $("scanCameraPrompt").classList.remove("hidden");
  } else {
    $("scanCameraPrompt").innerHTML = "等待手机摄像头画面<br><small>开始本题时自动启动扫码</small>";
    $("scanCameraPrompt").classList.toggle("hidden", !!meta.camera_ok || running);
  }
}

async function endAnswerAndShowResults() {
  if (state?.phase === "question" && !state.auto_mode) {
    let ended = false;
    await withBusy(async () => { await control("end"); ended = true; });
    if (!ended) return;
    if (state?.phase === "question") return;
  }
  nativeBridge()?.stopCamera?.();
  setScanTab("graph", true);
}

function setNotice(id, text, kind = "") {
  const el = $(id);
  el.textContent = text;
  el.className = `notice${kind ? ` ${kind}` : ""}`;
}

function showToast(message) {
  const el = $("toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 3500);
}

function setMobileView(view, { animate = true } = {}) {
  const titles = { classroom: "课堂", library: "测验", more: "更多" };
  const selected = ["classroom", "library", "more"].includes(view) ? view : "classroom";
  const order = ["classroom", "library", "more"];
  const previous = document.body.dataset.mobileView || "classroom";
  const direction = order.indexOf(selected) > order.indexOf(previous) ? "next"
    : order.indexOf(selected) < order.indexOf(previous) ? "previous" : "";
  if (animate && direction) {
    document.body.dataset.mobileTransition = direction;
    if (mobileTransitionTimer !== null) clearTimeout(mobileTransitionTimer);
    mobileTransitionTimer = setTimeout(() => {
      delete document.body.dataset.mobileTransition;
      mobileTransitionTimer = null;
    }, 300);
  } else {
    delete document.body.dataset.mobileTransition;
  }
  document.body.dataset.mobileView = selected;
  try { sessionStorage.setItem("quizscanner.mobile-view.v1", selected); } catch {}
  $("destinationName").textContent = titles[selected];
  $("homeNav").querySelectorAll("button[data-view]").forEach(button => {
    const active = button.dataset.view === selected;
    button.classList.toggle("active", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
  window.scrollTo({ top: 0, behavior: animate ? "smooth" : "auto" });
}

function updateNativeCameraStatus(message, running) {
  const button = $("nativeCameraButton");
  if (!button) return;
  button.textContent = running ? "停止本机摄像头" : "开启本机摄像头扫码";
  button.classList.toggle("camera-is-running", !!running);
  const status = $("nativeCameraStatus");
  if (status && message) status.textContent = message;
}

window.setNativeCameraStatus = updateNativeCameraStatus;

function initializeNativeControls() {
  const bridge = nativeBridge();
  const panel = $("nativeAndroidTools");
  if (!bridge || !panel) return;
  panel.classList.remove("hidden");
  try { $("computerAddress").value = bridge.getServerAddress?.() || ""; } catch {}
  let choices = [];
  try { choices = JSON.parse(bridge.getCameraChoicesJson?.() || "[]"); } catch {}
  const select = $("cameraLensSelect");
  select.replaceChildren();
  const automatic = document.createElement("option");
  automatic.value = "";
  automatic.textContent = "自动选择主摄";
  select.appendChild(automatic);
  choices.forEach(choice => {
    const option = document.createElement("option");
    option.value = choice.id;
    option.textContent = choice.label;
    select.appendChild(option);
  });
  const showLens = choices.length > 1;
  $("cameraLensLabel").classList.toggle("hidden", !showLens);
  select.classList.toggle("hidden", !showLens);
  try { select.value = bridge.getPreferredCameraId?.() || ""; } catch {}
  updateNativeCameraStatus("连接电脑后，开始作答时手机会自动扫码。", !!bridge.isCameraRunning?.());
}

window.onNativeMobilePageReady = initializeNativeControls;

function renderAnswers(question, reveal) {
  const box = $("answers");
  box.replaceChildren();
  if (!question || !Array.isArray(question.answers)) return;
  question.answers.forEach((text, index) => {
    const row = document.createElement("div");
    row.className = "answer";
    if (reveal && question.correct === index) row.classList.add("correct");
    const letter = document.createElement("span");
    letter.className = "answer-letter";
    letter.textContent = LETTERS[index];
    const value = document.createElement("span");
    value.textContent = text || "（空选项）";
    row.append(letter, value);
    box.appendChild(row);
  });
}

function renderStudents(data) {
  const body = $("studentAnswers");
  body.replaceChildren();
  const students = data.students || {};
  const rows = Object.values(students).sort((a, b) =>
    String(a.student_no || "").localeCompare(String(b.student_no || ""), "zh-CN", { numeric: true }));
  if (!rows.length) {
    const row = document.createElement("tr");
    row.innerHTML = '<td colspan="4" class="empty-row">尚未识别到答题卡</td>';
    body.appendChild(row);
  } else {
    const correctLetter = data.question && Number.isInteger(data.question.correct)
      && data.question.correct >= 0 && data.question.correct < 4
      ? LETTERS[data.question.correct] : null;
    const showCorrect = ["reveal", "podium"].includes(data.phase) && correctLetter;
    rows.forEach(student => {
      const row = document.createElement("tr");
      const idCell = document.createElement("td"); idCell.textContent = student.student_no || student.id || "";
      const nameCell = document.createElement("td"); nameCell.textContent = student.name || "（未填写姓名）";
      const answerCell = document.createElement("td");
      const chip = document.createElement("span");
      chip.className = "answer-chip";
      if (showCorrect) chip.classList.add(student.answer === correctLetter ? "good" : "bad");
      chip.textContent = student.answer || "—";
      answerCell.appendChild(chip);
      const scoreCell = document.createElement("td");
      scoreCell.textContent = String((data.scores || {})[student.key] || 0);
      row.append(idCell, nameCell, answerCell, scoreCell);
      body.appendChild(row);
    });
  }

  const leaderboard = $("leaderboard");
  leaderboard.replaceChildren();
  const leaders = data.leaderboard || [];
  if (!leaders.length) {
    const li = document.createElement("li"); li.className = "empty-row"; li.textContent = "暂无排名";
    leaderboard.appendChild(li);
  } else {
    leaders.forEach((person, index) => {
      const li = document.createElement("li");
      const label = document.createElement("span");
      label.textContent = String(index + 1) + ". " + (person.student_no || person.id || "") + "　" + (person.name || "");
      const score = document.createElement("span");
      score.className = "score"; score.textContent = `${person.score} 分`;
      li.append(label, score); leaderboard.appendChild(li);
    });
  }
}

function render(data, meta, settings) {
  state = data;
  observeScanPhase(data);
  if (!stagedRoster && data.active_class && currentRoster.active_class !== data.active_class) {
    currentRoster.active_class = data.active_class;
    renderRoster();
  }
  const hasQuestion = !!data.total && !!data.question;
  $("counter").textContent = hasQuestion
    ? `第 ${data.index + 1} 题 / 共 ${data.total} 题`
    : "尚未加载测验";
  $("phase").textContent = ({
    idle: "准备中", question: "答题中", ended: "作答已结束", reveal: "已公布", podium: "测验结束",
  })[data.phase] || "等待中";
  $("phase").className = `phase ${data.phase || ""}`;
  $("questionText").textContent = data.question?.text || (hasQuestion ? "（本题无题干文字）" : "请先加载一份测验");
  if (!scanVisible) renderAnswers(data.question, ["reveal", "podium"].includes(data.phase));
  $("answered").textContent = data.answered ?? 0;
  $("timeLeft").textContent = data.time_left == null ? "不限时" : `${Math.ceil(data.time_left)} 秒`;
  if (document.activeElement !== $("noCountdownToggle"))
    $("noCountdownToggle").checked = data.countdown_enabled === false;
  const d = data.distribution || {};
  $("distribution").textContent = LETTERS.map(letter => `${letter} ${d[letter] || 0}`).join("　");

  const cameraOK = !!meta.camera_ok;
  const cameraState = $("cameraStatus");
  cameraState.textContent = cameraOK ? "已连接" : "未连接";
  cameraState.className = `camera-state ${cameraOK ? "ok" : "error"}`;
  setNotice("cameraMessage", cameraOK
    ? "手机视频已接入，QuizScanner 正在分析画面。开始本题后会记录稳定识别到的答案。"
    : "摄像头尚未传回画面。请先在安卓 IP Webcam 启动服务器，再在下方填写视频地址。", cameraOK ? "ok" : "");

  const auto = !!data.auto_mode;
  $("autoNotice").classList.toggle("hidden", !auto);
  if (document.activeElement !== $("autoToggle")) $("autoToggle").checked = auto;
  if (document.activeElement !== $("speedToggle")) $("speedToggle").checked = !!data.speed_bonus;
  if (document.activeElement !== $("onlyKnownToggle")) $("onlyKnownToggle").checked = settings.only_known !== false;
  if (document.activeElement !== $("showStudentAnswersToggle"))
    $("showStudentAnswersToggle").checked = settings.show_student_answers_on_reveal !== false;
  $("previousButton").disabled = busy || auto || !hasQuestion;
  $("startButton").disabled = busy || auto || !hasQuestion || data.phase !== "idle";
  $("revealButton").disabled = busy || auto || !hasQuestion || !["question", "ended"].includes(data.phase);
  $("noCountdownToggle").disabled = busy || auto || data.phase !== "idle";
  $("autoToggle").disabled = busy || data.countdown_enabled === false;
  $("nextButton").disabled = busy || auto || !hasQuestion;
  $("previousButton").disabled ||= busy || auto || !hasQuestion || data.index <= 0;
  $("nextButton").textContent = hasQuestion && data.index >= data.total - 1
    ? "结束测验并查看排名" : "下一题并开始";
  $("loadButton").disabled = busy || !$("quizSelect").value;
  $("connectCameraButton").disabled = busy;
  $("resetButton").disabled = busy || !data.total;
  $("saveRosterButton").disabled = busy || !stagedRoster;
  $("classSelect").disabled = busy || !currentRoster.classes?.length || ["question", "ended", "reveal"].includes(data.phase);
  const rosterForCards = stagedRoster || currentRoster;
  $("cardsButton").disabled = busy || !(rosterForCards.students || []).some(
    student => student.class_name === rosterForCards.active_class);
  if (!scanVisible) renderStudents(data);
  renderScanExperience(data, meta);
}

async function refresh() {
  if (busy || refreshing) return;
  refreshing = true;
  try {
    const data = await api("/api/state?full=1&live=1");
    if (state && data.session_id === state.session_id && data.revision < state.revision) return;
    const refreshSettingsAfter = scanVisible ? 5000 : 3000;
    if (!cachedSettings || Date.now() - settingsFetchedAt > refreshSettingsAfter) {
      const result = await api("/api/settings");
      cachedSettings = result.settings || result;
      settingsFetchedAt = Date.now();
    }
    const settings = cachedSettings || {};
    const meta = { camera_ok: !!data.camera_ok };
    if (!settingsLoaded || document.activeElement !== $("cameraSource")) {
      const cameraSource = settings.camera ?? "0";
      $("cameraSource").value = cameraSource === "android" ? "" : cameraSource;
      settingsLoaded = true;
    }
    render(data, meta, settings);
    setNotice("connectionStatus", `已连接电脑服务：${location.host}`, "ok");
  } catch (error) {
    setNotice("connectionStatus", `无法连接电脑服务：${error.message}。请确认电脑上的 QuizScanner 已启动，手机和电脑处于同一 Wi‑Fi。`, "error");
  } finally { refreshing = false; }
}

async function withBusy(task, noticeId = "connectionStatus") {
  if (busy) return;
  busy = true;
  try {
    await task();
  } catch (error) {
    setNotice(noticeId, `操作失败：${error.message}`, "error");
  } finally {
    busy = false;
    await refresh();
  }
}

async function loadQuizList() {
  try {
    const result = await api("/api/quizzes");
    renderQuizCollections(result);
    const select = $("quizSelect");
    select.replaceChildren();
    if (!result.quizzes?.length) {
      const option = document.createElement("option");
      option.value = ""; option.textContent = "暂无测验，请上传 Word 或到题目编辑器创建";
      select.appendChild(option);
      return;
    }
    result.quizzes.forEach(name => {
      const option = document.createElement("option");
      option.value = name; option.textContent = name;
      option.selected = name === result.active;
      select.appendChild(option);
    });
  } catch (error) {
    setNotice("connectionStatus", `无法读取测验列表：${error.message}`, "error");
  }
}

function getRecentQuizzes() {
  try {
    const saved = JSON.parse(localStorage.getItem(RECENT_QUIZZES_KEY) || "[]");
    return Array.isArray(saved) ? saved.filter(item => item && typeof item.name === "string") : [];
  } catch { return []; }
}

function rememberRecentQuiz(name) {
  if (!name) return;
  const recent = getRecentQuizzes().filter(item => item.name !== name);
  recent.unshift({ name, opened_at: Date.now() });
  try { localStorage.setItem(RECENT_QUIZZES_KEY, JSON.stringify(recent.slice(0, 10))); } catch {}
}

function quizLibraryRow(name, count, active, recentTime) {
  const row = document.createElement("article");
  row.className = `quiz-library-row${active ? " current" : ""}`;
  const play = document.createElement("button");
  play.className = "quiz-library-play";
  play.type = "button";
  play.setAttribute("aria-label", `加载测验：${name}`);
  play.textContent = "▶";
  play.addEventListener("click", () => loadQuizByName(name));
  const copy = document.createElement("div");
  copy.className = "quiz-library-copy";
  const title = document.createElement("strong");
  title.textContent = name;
  const meta = document.createElement("span");
  const when = recentTime
    ? `最近打开 · ${new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric" }).format(new Date(recentTime))}`
    : (active ? "当前测验" : "测验库");
  meta.textContent = `${when} · ${count} 道题`;
  copy.append(title, meta);
  const badge = document.createElement("span");
  badge.className = "quiz-library-count";
  badge.textContent = String(count);
  row.append(play, copy, badge);
  return row;
}

function renderQuizCollections(result) {
  quizCatalog = result || { quizzes: [], active: null, details: [] };
  result = quizCatalog;
  const names = result.quizzes || [];
  const details = new Map((result.details || []).map(item => [item.name, Number(item.question_count) || 0]));
  const library = $("quizLibraryList");
  library.replaceChildren();
  if (!names.length) {
    const empty = document.createElement("div");
    empty.className = "quiz-library-empty";
    empty.textContent = "测验库为空。上传 Word 选择题或到题目编辑器创建测验。";
    library.appendChild(empty);
  } else {
    names.forEach(name => library.appendChild(quizLibraryRow(
      name, details.get(name) || 0, name === result.active, 0)));
  }

  const recentPanel = $("recentPanel");
  recentPanel.replaceChildren();
  const available = new Set(names);
  const recent = getRecentQuizzes().filter(item => available.has(item.name));
  if (!recent.length) {
    const empty = document.createElement("div");
    empty.className = "quiz-library-empty";
    empty.textContent = "最近打开的测验会显示在这里。";
    recentPanel.appendChild(empty);
  } else {
    recent.forEach(item => recentPanel.appendChild(quizLibraryRow(
      item.name, details.get(item.name) || 0, item.name === result.active, item.opened_at)));
  }
}

async function loadQuizByName(name) {
  if (!name) return;
  await withBusy(async () => {
    await api("/api/load", { name });
    rememberRecentQuiz(name);
    await loadQuizList();
    setMobileView("classroom");
    showToast(`已加载测验：${name}`);
  });
}

function readBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("文件读取失败"));
    reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
    reader.readAsDataURL(file);
  });
}

function renderDocxPreview(result) {
  stagedQuiz = result.quiz;
  $("docxTitle").textContent = stagedQuiz.title || "导入测验";
  $("docxSummary").textContent = `识别到 ${result.question_count} 道选择题；${result.missing_answers ? `有 ${result.missing_answers} 道题缺少答案，需要逐题补选。` : "请核对题干、选项和答案。"}`;
  const box = $("docxQuestions");
  box.replaceChildren();
  stagedQuiz.questions.forEach((question, index) => {
    const card = document.createElement("article"); card.className = "docx-question";
    const title = document.createElement("strong"); title.textContent = `${index + 1}. ${question.text}`;
    const list = document.createElement("ul");
    question.answers.forEach((answer, ai) => {
      const li = document.createElement("li"); li.textContent = `${LETTERS[ai]}. ${answer}`; list.appendChild(li);
    });
    const label = document.createElement("label"); label.textContent = "正确答案";
    const select = document.createElement("select"); select.dataset.question = String(index);
    const empty = document.createElement("option"); empty.value = ""; empty.textContent = "请选择"; select.appendChild(empty);
    LETTERS.forEach((letter, ai) => {
      const option = document.createElement("option");
      option.value = String(ai); option.textContent = `${letter}. ${question.answers[ai]}`;
      option.selected = question.correct === ai;
      select.appendChild(option);
    });
    select.addEventListener("change", () => { question.correct = select.value === "" ? -1 : Number(select.value); });
    label.appendChild(select);
    card.append(title, list, label);
    box.appendChild(card);
  });
  $("mobileDocxTools").open = true;
  setMobileView("library");
  $("docxPreview").classList.remove("hidden");
  $("docxPreview").scrollIntoView({ behavior: "smooth", block: "start" });
}

$("loadButton").addEventListener("click", () => loadQuizByName($("quizSelect").value));

function selectQuizView(view) {
  const recent = view === "recent";
  $("libraryPanel").classList.toggle("hidden", recent);
  $("recentPanel").classList.toggle("hidden", !recent);
  $("libraryTab").classList.toggle("active", !recent);
  $("recentTab").classList.toggle("active", recent);
  $("libraryTab").setAttribute("aria-selected", String(!recent));
  $("recentTab").setAttribute("aria-selected", String(recent));
}

$("libraryTab").addEventListener("click", () => selectQuizView("library"));
$("recentTab").addEventListener("click", () => selectQuizView("recent"));
$("homeNav").querySelectorAll("button[data-view]").forEach(button => {
  button.addEventListener("click", () => setMobileView(button.dataset.view));
});

const PAGE_SWIPE_VIEWS = ["classroom", "library", "more"];
$("main").addEventListener("touchstart", event => {
  if (scanVisible || event.touches.length !== 1) { pageTouchStart = null; return; }
  if (event.target.closest("input, textarea, select, button, a, [role='tab'], .table-scroll, .scan-graph-panel, .scan-students-panel")) {
    pageTouchStart = null;
    return;
  }
  const touch = event.touches[0];
  pageTouchStart = { x: touch.clientX, y: touch.clientY, at: Date.now() };
}, { passive: true });

$("main").addEventListener("touchend", event => {
  if (!pageTouchStart || scanVisible || !event.changedTouches.length) return;
  const start = pageTouchStart;
  pageTouchStart = null;
  const touch = event.changedTouches[0];
  const dx = touch.clientX - start.x;
  const dy = touch.clientY - start.y;
  if (Date.now() - start.at > 850 || Math.abs(dx) < 58 || Math.abs(dx) < Math.abs(dy) * 1.35) return;
  const index = PAGE_SWIPE_VIEWS.indexOf(document.body.dataset.mobileView || "classroom");
  const nextIndex = Math.max(0, Math.min(PAGE_SWIPE_VIEWS.length - 1, index + (dx < 0 ? 1 : -1)));
  if (nextIndex !== index) setMobileView(PAGE_SWIPE_VIEWS[nextIndex]);
}, { passive: true });

$("startButton").addEventListener("click", () => {
  enterScanExperience(true);
  return withBusy(() => control("start", {
    countdown_enabled: !$("noCountdownToggle").checked,
  }));
});
$("revealButton").addEventListener("click", () => withBusy(() => control("reveal")));
$("previousButton").addEventListener("click", () => withBusy(() => control("prev_start")));
$("resumeScanButton").addEventListener("click", () => enterScanExperience(true));
$("exitScanButton").addEventListener("click", () => exitScanExperience({ dismissed: true }));
$("scanGraphTab").addEventListener("click", () =>
  setScanTab("graph", !(scanDrawerOpen && scanDrawerTab === "graph")));
$("scanStudentsTab").addEventListener("click", () =>
  setScanTab("students", !(scanDrawerOpen && scanDrawerTab === "students")));
$("scanDrawerHandle").addEventListener("click", () => {
  setScanTab(scanDrawerTab, !scanDrawerOpen);
});
$("scanEndButton").addEventListener("click", endAnswerAndShowResults);
$("scanShowAnswersToggle").addEventListener("change", event => withBusy(() => api("/api/settings", {
  show_student_answers_on_reveal: event.target.checked,
})));
$("scanNextButton").addEventListener("click", () => withBusy(() => control("next_start")));

$("scanCameraButton").addEventListener("click", endAnswerAndShowResults);
$("nextButton").addEventListener("click", () => withBusy(() => control("next_start")));

$("resetButton").addEventListener("click", () => {
  if (confirm("确定清空全部得分并从第一题重新开始吗？")) {
    withBusy(() => control("reset"));
  }
});

$("autoToggle").addEventListener("change", event => {
  if (event.target.checked && $("noCountdownToggle").checked) {
    event.target.checked = false;
    showToast("不限时模式需要教师手动结束作答，不能启用自动模式。");
    return;
  }
  withBusy(() => control("auto_mode", { value: event.target.checked }));
});
$("noCountdownToggle").addEventListener("change", event =>
  withBusy(() => api("/api/settings", { countdown_enabled: !event.target.checked })));
$("speedToggle").addEventListener("change", event => withBusy(() => control("speed_bonus", { value: event.target.checked })));
$("onlyKnownToggle").addEventListener("change", event => withBusy(() => api("/api/settings", { only_known: event.target.checked })));
$("showStudentAnswersToggle").addEventListener("change", event =>
  withBusy(() => api("/api/settings", {
    show_student_answers_on_reveal: event.target.checked,
  })));

$("connectCameraButton").addEventListener("click", () => withBusy(async () => {
  const source = $("cameraSource").value.trim();
  if (!/^https?:\/\//i.test(source)) throw new Error("请输入 IP Webcam 视频流完整地址，示例以 http:// 开头并以 /video 结尾。");
  await api("/api/settings", { camera: source });
  setNotice("cameraMessage", "已提交地址，正在连接手机视频并启动识别。请保持 IP Webcam 运行。", "");
}));

$("connectComputerButton").addEventListener("click", () => {
  const bridge = nativeBridge();
  if (!bridge?.connectToComputer?.($("computerAddress").value.trim())) {
    setNotice("connectionStatus", "请输入带端口的电脑局域网地址，例如 http://192.168.137.1:8012。", "error");
  }
});
$("openWifiSettingsButton").addEventListener("click", () => nativeBridge()?.openWifiSettings?.());
$("nativeCameraButton").addEventListener("click", () => {
  const bridge = nativeBridge();
  if (!bridge) return;
  if (bridge.isCameraRunning?.()) bridge.stopCamera?.();
  else bridge.startCamera?.();
});
$("cameraLensSelect").addEventListener("change", event => {
  if (!nativeBridge()?.setPreferredCameraId?.(event.target.value)) {
    showToast("请先停止摄像头，再切换后置镜头。");
    initializeNativeControls();
  }
});

$("chooseDocxButton").addEventListener("click", () => $("docxFile").click());
$("docxFile").addEventListener("change", async event => {
  const file = event.target.files?.[0]; event.target.value = "";
  if (!file) return;
  if (file.size > MAX_DOCX_BYTES) { setNotice("connectionStatus", "DOCX 文件不能超过 8 MB。", "error"); return; }
  await withBusy(async () => {
    setNotice("connectionStatus", "正在读取 Word 文档中的选择题…");
    const result = await api("/api/quiz/import-docx", {
      filename: file.name, content_base64: await readBase64(file),
    });
    renderDocxPreview(result);
    setNotice("connectionStatus", "Word 题目已解析。请核对每道题的题干、选项和正确答案，再导入测验。", "ok");
  });
});

$("cancelDocxButton").addEventListener("click", () => {
  stagedQuiz = null;
  $("docxPreview").classList.add("hidden");
  $("docxQuestions").replaceChildren();
});
$("saveDocxButton").addEventListener("click", () => withBusy(async () => {
  if (!stagedQuiz) return;
  const missing = stagedQuiz.questions.findIndex(question => !Number.isInteger(question.correct) || question.correct < 0 || question.correct > 3);
  if (missing >= 0) throw new Error(`第 ${missing + 1} 题尚未选择正确答案。`);
  const result = await api("/api/quiz/import", { name: stagedQuiz.title || "语文测验", quiz: stagedQuiz });
  stagedQuiz = null;
  $("docxPreview").classList.add("hidden");
  await api("/api/load", { name: result.name });
  rememberRecentQuiz(result.name);
  await loadQuizList();
  $("quizSelect").value = result.name;
  setMobileView("classroom");
  setNotice("connectionStatus", `已导入并加载“${result.name}”。`, "ok");
}));

async function loadRoster() {
  try {
    currentRoster = await api("/api/roster");
    stagedRoster = null;
    renderRoster();
  } catch (error) {
    setNotice("rosterMessage", `读取学生名单失败：${error.message}`, "error");
  }
}

function renderRoster() {
  const roster = stagedRoster || currentRoster;
  const classes = roster.classes || [];
  const classSelect = $("classSelect");
  if (document.activeElement !== classSelect) {
    classSelect.replaceChildren();
    if (!classes.length) {
      const option = document.createElement("option");
      option.value = ""; option.textContent = "请先上传包含班级的名单";
      classSelect.appendChild(option);
    } else {
      classes.forEach(className => {
        const option = document.createElement("option");
        option.value = className; option.textContent = className;
        option.selected = className === roster.active_class;
        classSelect.appendChild(option);
      });
    }
  }
  classSelect.disabled = busy || !classes.length || ["question", "ended", "reveal"].includes(state?.phase);
  const list = $("rosterList");
  list.replaceChildren();
  const className = roster.active_class || classes[0] || "";
  const classStudents = (roster.students || []).filter(student => student.class_name === className)
    .sort((a, b) => String(a.student_no || "").localeCompare(String(b.student_no || ""), "zh-CN", { numeric: true }));
  classStudents.forEach(student => {
    const li = document.createElement("li");
    li.textContent = student.student_no + "　" + (student.name || "（未填写姓名）") + "　卡号 " + student.card_id;
    list.appendChild(li);
  });
  const count = (roster.students || []).length;
  if (stagedRoster) setNotice("rosterMessage", "已预览 " + count + " 名学生、" + classes.length + " 个班级。当前显示 " + (className || "未分班") + "；核对后保存名单。", "ok");
  else setNotice("rosterMessage", "已保存名单：" + classes.length + " 个班级、" + count + " 名学生。当前班级 " + (className || "未分班") + "，" + classStudents.length + " 人。", count ? "ok" : "");
  $("saveRosterButton").disabled = busy || !stagedRoster;
  $("cardsButton").disabled = busy || !classStudents.length;
}

$("classSelect").addEventListener("change", event => withBusy(async () => {
  const className = event.target.value;
  if (!className) return;
  if (stagedRoster) {
    stagedRoster.active_class = className;
    renderRoster();
    return;
  }
  const result = await api("/api/roster/class", { class_name: className });
  currentRoster.active_class = result.active_class;
  renderRoster();
}, "rosterMessage"));

$("chooseRosterButton").addEventListener("click", () => $("rosterFile").click());
$("rosterFile").addEventListener("change", async event => {
  const file = event.target.files?.[0]; event.target.value = "";
  if (!file) return;
  if (file.size > MAX_ROSTER_BYTES) { setNotice("rosterMessage", "名单文件不能超过 3 MB。", "error"); return; }
  await withBusy(async () => {
    const result = await api("/api/roster/import", {
      filename: file.name, content_base64: await readBase64(file),
    });
    if ((currentRoster.students || []).length && !confirm("导入的 " + result.count + " 名学生将替换当前编辑名单。已保存名单在点击“保存名单”前不会改变。继续吗？")) return;
    stagedRoster = result.roster;
    renderRoster();
  }, "rosterMessage");
});

$("saveRosterButton").addEventListener("click", () => withBusy(async () => {
  if (!stagedRoster) return;
  const result = await api("/api/roster", stagedRoster);
  currentRoster = result.roster;
  stagedRoster = null;
  renderRoster();
}));

$("cardsButton").addEventListener("click", () => withBusy(async () => {
  const roster = stagedRoster || currentRoster;
  const className = roster.active_class || roster.classes?.[0];
  if (!className || !(roster.students || []).some(student => student.class_name === className)) {
    throw new Error("请先选择有学生的班级。");
  }
  if (stagedRoster) {
    const result = await api("/api/roster", roster);
    currentRoster = result.roster;
    stagedRoster = null;
  }
  renderRoster();
  const link = document.createElement("a");
  link.href = "/api/cards.pdf?class=" + encodeURIComponent(className);
  link.download = "QuizScanner-" + className + "-学生答题卡.pdf";
  document.body.appendChild(link); link.click(); link.remove();
  showToast("已生成学生答题卡 PDF。");
}));

initializeNativeControls();
try {
  const savedView = sessionStorage.getItem("quizscanner.mobile-view.v1");
  if (["classroom", "library", "more"].includes(savedView)) setMobileView(savedView, { animate: false });
} catch {}
loadQuizList().then(refresh);
loadRoster();
scheduleMobileRefresh();
