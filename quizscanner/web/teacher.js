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
let lastTeacherState = null;
let controlInFlight = false;
const ctl = async (action, extra) => {
  if (controlInFlight) return;
  controlInFlight = true;
  try {
    const result = await api("/api/control", Object.assign({ action,
      expected_attempt: lastTeacherState?.attempt_id, command_id: String(Date.now()) + Math.random() }, extra || {}));
    if (result.ok === false) throw new Error(result.error);
    lastTeacherState = result.state;
    return result;
  } catch (error) { alert(error.message); } finally { controlInFlight = false; }
};

// ---- sterowanie quizem ----
$("startBtn").onclick = () => ctl("start", {
  countdown_enabled: !$("noCountdownToggle").checked
});
$("endBtn").onclick = () => ctl("end");
$("revealBtn").onclick = () => ctl("reveal");
$("nextBtn").onclick = () => ctl("next_start");
$("prevBtn").onclick = () => ctl("prev_start");
$("resetBtn").onclick = () => { if (confirm(t("t_confirm_reset"))) ctl("reset"); };
$("speedToggle").onchange = () => ctl("speed_bonus", { value: $("speedToggle").checked });
$("autoToggle").onchange = () => {
  if ($("autoToggle").checked && $("noCountdownToggle").checked) {
    $("autoToggle").checked = false;
    alert("无倒计时模式需要教师手动结束作答，不能同时启用自动模式。");
    return;
  }
  ctl("auto_mode", { value: $("autoToggle").checked });
};
$("classSel").onchange = async () => {
  if (!$("classSel").value) return;
  await api("/api/roster/class", { class_name: $("classSel").value });
  refreshState();
};
$("scanVisibilitySel").onchange = () =>
  api("/api/settings", { scan_visibility: $("scanVisibilitySel").value });
$("showStudentAnswersToggle").onchange = () =>
  api("/api/settings", {
    show_student_answers_on_reveal: $("showStudentAnswersToggle").checked
  });
$("noCountdownToggle").onchange = () =>
  api("/api/settings", { countdown_enabled: !$("noCountdownToggle").checked });
$("editorBtn").onclick = () => window.open("/editor", "_blank");
$("boardBtn").onclick = () => window.open("/board", "_blank");
$("mobileBtn").onclick = () => window.open("/mobile", "_blank");
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
$("themeSel").onchange = async () => {
  setTheme($("themeSel").value);          // od razu widać, bez czekania na serwer
  await api("/api/settings", { theme: $("themeSel").value });
};
$("onlyKnownToggle").onchange = () =>
  api("/api/settings", { only_known: $("onlyKnownToggle").checked });
$("autoReportToggle").onchange = () =>
  api("/api/settings", { auto_report: $("autoReportToggle").checked });
$("updateToggle").onchange = async () => {
  await api("/api/settings", { check_updates: $("updateToggle").checked });
  checkUpdate();
};
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
        <li>Podłącz telefon do <b>tej samej sieci Wi-Fi</b> co komputer albo do hotspotu komputera.</li>
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
        <li>Connect both devices to the <b>same Wi-Fi network</b>, or connect the phone to the computer hotspot.</li>
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
  zh: {
    title: "用手机代替电脑摄像头",
    body: `
      <ol>
        <li>在手机上安装免费的视频串流应用：安卓可用 <b>IP Webcam</b>，安卓和 iPhone 可用 <b>Iriun Webcam</b> 或 <b>DroidCam</b>。</li>
        <li>将手机和电脑连接到<b>同一个 Wi-Fi 网络</b>，或让手机连接电脑热点。</li>
        <li>打开手机应用并点击“启动服务器”。应用会显示一个地址，例如
          <code>http://192.168.1.50:8080</code>。</li>
        <li>在这里输入视频地址并点击<b>切换</b>：
          <ul>
            <li>IP Webcam：<code>http://192.168.1.50:8080/video</code></li>
            <li>DroidCam：<code>http://192.168.1.50:4747/video</code></li>
          </ul></li>
        <li>调整手机位置，让摄像头能够拍到全班答题卡。建议使用三脚架或放在稳固的支撑物上。</li>
      </ol>
      <p><b>提示：</b>Iriun 和 DroidCam 也提供电脑客户端，可在系统中创建一个普通摄像头。安装后可在图像来源处输入摄像头编号，例如 <code>1</code> 或 <code>2</code>。</p>`,
  },
};
function showPhoneHelp() {
  const h = PHONE_HELP[document.documentElement.lang] || PHONE_HELP.zh;
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
  const address = m.hotspot_ip || m.lan_ip;
  const base = `http://${address}:${m.port}`;
  $("lanUrl").innerHTML =
    `${t("t_lan_board")}: <a href="${base}/board" target="_blank" rel="noopener"><b>${base}/board</b></a><br>` +
    `${t("t_mobile_remote")}: <a href="${base}/mobile" target="_blank" rel="noopener"><b>${base}/mobile</b></a>`;
}

async function loadSettings() {
  const s = await api("/api/settings");
  $("langSel").value = s.lang || "zh";
  $("camSrc").value = s.camera != null ? s.camera : "0";
  $("onlyKnownToggle").checked = !!s.only_known;
  $("autoReportToggle").checked = s.auto_report !== false;
  $("updateToggle").checked = s.check_updates !== false;
}

// ---- raport ----
const REPORT_FORMATS = ["pdf", "xlsx", "csv", "html", "json", "txt"];

function reportRow(st, total) {
  return `<tr><td class="p">${st.place}</td><td>${esc(st.name)}</td>
    <td class="n">#${st.id}</td><td class="n">${st.score}</td>
    <td class="n">${st.correct}/${total}</td><td class="n">${st.percent}%</td></tr>`;
}

function reportQuery() {
  const query = new URLSearchParams();
  if ($("reportSession").value) query.set("session", $("reportSession").value);
  if ($("reportClass").value) query.set("class", $("reportClass").value);
  return query;
}
async function refreshReport() { renderReport(await api("/api/report/preview?" + reportQuery())); }
function renderReport(r) {
  const s = r.summary;
  if (!s.questions) {
    $("repBody").innerHTML = `<p class="muted">${t("r_empty")}</p>`;
  } else {
    const hardest = s.hardest_n
      ? `<p class="muted">${t("r_hardest")}: <b>${s.hardest_n}.</b> ${tex(s.hardest_text)}
         — ${s.hardest_percent}%</p>` : "";
    $("repBody").innerHTML = `
      <div class="rep-cards">
        <div class="stat"><div class="k">${t("r_stat_students")}</div><div class="v">${s.students}</div></div>
        <div class="stat"><div class="k">${t("r_stat_questions")}</div><div class="v">${s.questions}</div></div>
        <div class="stat"><div class="k">${t("r_stat_avg")}</div><div class="v">${s.avg_percent}%</div></div>
        <div class="stat"><div class="k">${t("r_stat_best")}</div><div class="v sm">${esc(s.best || "—")}</div></div>
      </div>
      ${hardest}
      <table class="students rep-table"><thead><tr>
        <th>${t("r_col_place")}</th><th>${t("r_col_student")}</th><th>${t("t_col_id")}</th>
        <th>${t("r_col_points")}</th><th>${t("r_col_correct")}</th><th>${t("r_col_percent")}</th>
      </tr></thead><tbody>
        ${r.students.map(st => reportRow(st, s.questions)).join("")}
      </tbody></table>
      <h3>每题作答情况</h3>${r.questions.map(question => `<details><summary>第 ${question.n} 题 · ${esc(question.text_plain)} · ${question.answered} 人作答</summary>
      ${LETTERS.map(letter => `<p>${letter}：${question.distribution[letter]} 人 · ${esc((question.students_by_option?.[letter] || []).join("、"))}</p>`).join("")}
      <p>未作答：${esc((question.unanswered_students || []).join("、") || "无")}</p></details>`).join("")}`;
  }

  $("repFormats").innerHTML = REPORT_FORMATS.map(f =>
    `<button class="btn-ghost fmt" data-fmt="${f}">${t("r_fmt_" + f)}</button>`).join("");
  $("repFormats").querySelectorAll("button").forEach(b => {
    b.onclick = () => window.open("/api/report?" + reportQuery() + "&format=" + b.dataset.fmt, "_blank");
  });

  const saved = (r.saved || []).slice(0, 8);
  $("repSaved").innerHTML = `<div class="field">${t("r_open_folder")}</div>
    <code>${esc(r.dir || "")}</code>
    <div class="field mt">${t("r_recent")}</div>` + (saved.length
      ? `<ul class="rep-files">${saved.map(f =>
          `<li>${esc(f.file)} <span class="muted">${Math.round(f.size / 1024)} kB</span></li>`).join("")}</ul>`
      : `<p class="muted">${t("r_no_recent")}</p>`);
}

async function openReport() {
  $("reportModal").classList.remove("hidden");
  $("repBody").innerHTML = "…";
  const sessions = await api("/api/sessions");
  $("reportSession").innerHTML = `<option value="">当前课堂</option>` + sessions.sessions.map(item =>
    `<option value="${item.id}">${esc(item.title)} · ${esc(item.class_name)} · ${item.id.slice(0, 8)}</option>`).join("");
  const roster = await api("/api/roster");
  $("reportClass").innerHTML = roster.classes.map(name => `<option value="${esc(name)}" ${name === roster.active_class ? "selected" : ""}>${esc(name)}</option>`).join("");
  await refreshReport();
}

$("reportBtn").onclick = openReport;
$("repClose").onclick = () => $("reportModal").classList.add("hidden");
$("reportModal").onclick = e => {
  if (e.target === $("reportModal")) $("reportModal").classList.add("hidden");
};
$("repSave").onclick = async () => {
  const r = await api("/api/export", Object.fromEntries(reportQuery()));
  alert(r.ok ? t("r_saved_to") + "\n" + r.paths.join("\n") : t("r_empty"));
  await refreshReport();
};

// ---- aktualizacje ----
let updateInfo = null;

async function checkUpdate(force) {
  try {
    updateInfo = await api("/api/update" + (force ? "?force=1" : ""));
  } catch (e) { return; }
  const bar = $("updateBar");
  const state = $("updateState");
  if (updateInfo.disabled) { state.textContent = t("u_check_sub"); bar.classList.add("hidden"); return; }
  if (updateInfo.update) {
    $("updateText").textContent = t("u_available", {
      version: updateInfo.latest, current: updateInfo.current });
    $("updateBtn").classList.toggle("hidden", !updateInfo.can_apply);
    bar.classList.remove("hidden");
    state.textContent = t("u_available", {
      version: updateInfo.latest, current: updateInfo.current });
  } else {
    bar.classList.add("hidden");
    state.textContent = updateInfo.error ? t("u_check_sub") : t("u_up_to_date");
  }
}

$("updateClose").onclick = () => $("updateBar").classList.add("hidden");
$("updatePage").onclick = () =>
  window.open((updateInfo && updateInfo.url) || "https://github.com/PiotrKajor/QuizScanner/releases", "_blank");
$("updateBtn").onclick = async () => {
  $("updateText").textContent = t("u_downloading");
  $("updateBtn").disabled = true;
  const r = await api("/api/update/apply", {});
  $("updateBtn").disabled = false;
  if (r.ok) {
    $("updateText").textContent = t("u_ready");
    $("updateBtn").classList.add("hidden");
  } else if (r.error === "source") {
    $("updateText").textContent = t("u_source_hint");
    $("updateBtn").classList.add("hidden");
  } else {
    $("updateText").textContent = t("u_failed");
  }
};

// ---- render ----
function updateCamNote(cameraOk, nativeMode, nativeConnected) {
  const camera = $("cam");
  camera.classList.toggle("hidden", nativeMode);
  if (nativeMode) {
    camera.removeAttribute("src");
    const note = $("camNote");
    note.textContent = nativeConnected ? "手机教师端已连接，扫码画面在手机上显示。" : "手机教师端未连接，请检查手机与电脑的连接。";
    note.classList.remove("hidden");
    return;
  }
  if (!camera.getAttribute("src")) camera.src = "/video_feed";
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
      <span class="c">${tex(q.answers[i] || "")}</span>
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
  const rows = Object.values(students)
    .sort((a, b) => String(a.student_no || "").localeCompare(String(b.student_no || ""), "zh-CN", { numeric: true }))
    .map(s => {
    const ok = correctL && s.answer === correctL;
    const mark = correctL ? (ok ? '<span class="ans-ok">✓</span>' : '<span class="ans-bad">✗</span>') : "";
    return `<tr>
      <td>${esc(s.student_no || "")}</td><td>${esc(s.name)}</td>
      <td><span class="badge badge-sm badge-${s.answer}">${s.answer}</span> ${mark}</td>
      <td>${scores[s.key] || 0}</td></tr>`;
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

const PHASE_KEY = { idle: "idle", question: "question", ended: "reveal", reveal: "reveal", podium: "podium" };

function syncClassSelect(st) {
  const select = $("classSel");
  const classes = st.classes || [];
  const signature = JSON.stringify(classes);
  if (select.dataset.classes !== signature) {
    select.replaceChildren();
    classes.forEach(className => {
      const option = document.createElement("option");
      option.value = className; option.textContent = className;
      select.appendChild(option);
    });
    select.dataset.classes = signature;
  }
  if (document.activeElement !== select) select.value = st.active_class || "";
  select.disabled = !classes.length || !["idle", "ended", "reveal"].includes(st.phase);
}

async function refreshState() {
  let st;
  try { st = await api("/api/state?full=1"); } catch (e) { return; }
  lastTeacherState = st;
  syncClassSelect(st);
  const q = st.question;
  $("counter").textContent = st.total
    ? t("t_question_of", { n: st.index + 1, total: st.total }) : "—";
  const ph = $("phase");
  ph.textContent = ({ idle: "待开始", question: "正在作答", ended: "已结束", reveal: "已公布答案", podium: "测验结束" })[st.phase] || st.phase;
  ph.className = "phase " + (PHASE_KEY[st.phase] || "idle");
  $("qtext").innerHTML = q ? tex(q.text) : TeX.esc(t("t_load_quiz_first"));
  $("timeLeft").textContent = st.time_left != null ? Math.ceil(st.time_left) + " s" : "—";
  $("answered").textContent = st.answered;
  const d = st.distribution;
  $("dist").textContent = `${d.A}/${d.B}/${d.C}/${d.D}`;

  if (document.activeElement !== $("speedToggle")) $("speedToggle").checked = !!st.speed_bonus;
  if (document.activeElement !== $("autoToggle")) $("autoToggle").checked = !!st.auto_mode;
  if (document.activeElement !== $("onlyKnownToggle") && st.only_known != null)
    $("onlyKnownToggle").checked = !!st.only_known;
  if (document.activeElement !== $("scanVisibilitySel") && st.scan_visibility)
    $("scanVisibilitySel").value = st.scan_visibility;
  if (document.activeElement !== $("showStudentAnswersToggle"))
    $("showStudentAnswersToggle").checked = st.show_student_answers_on_reveal !== false;
  if (document.activeElement !== $("noCountdownToggle"))
    $("noCountdownToggle").checked = st.countdown_enabled === false;

  // Pasek trybu automatycznego + blokada przycisków ręcznych.
  const bar = $("autoBar");
  if (st.auto_mode) {
    bar.classList.remove("hidden");
    bar.textContent = t("t_auto_running") +
      (st.auto_next_in != null ? "  ·  " + Math.ceil(st.auto_next_in) + " s" : "");
  } else {
    bar.classList.add("hidden");
  }
  const hasQuestion = !!st.question;
  $("startBtn").disabled = !!st.auto_mode || !hasQuestion || !["idle", "ended", "reveal"].includes(st.phase);
  $("endBtn").disabled = !!st.auto_mode || st.phase !== "question";
  $("revealBtn").disabled = !!st.auto_mode || !["question", "ended"].includes(st.phase);
  $("nextBtn").disabled = !!st.auto_mode || st.phase === "podium";
  $("prevBtn").disabled = !!st.auto_mode || st.index <= 0 || st.phase === "question";
  $("resetBtn").disabled = !!st.auto_mode;
  $("noCountdownToggle").disabled = !!st.auto_mode || !["idle", "ended", "reveal"].includes(st.phase);

  renderOpts(st);
  renderStudents(st);
  renderLead(st);
  updateCamNote(st.camera_ok, st.input_source === "native", st.native_connected);
}

// Po zmianie języka odśwież teksty zależne od danych.
document.addEventListener("i18n:changed", () => {
  fillThemeSelect($("themeSel"));
  loadQuizList();
  loadMeta();
});

(async function init() {
  await initLang();
  fillThemeSelect($("themeSel"));
  $("themeSel").value = document.documentElement.dataset.theme || "dark";
  await loadSettings();
  $("langSel").value = document.documentElement.lang;
  loadQuizList();
  loadMeta();
  refreshState();
  checkUpdate();
  setInterval(refreshState, 500);
})();

$("pairPhoneBtn").onclick = async () => {
  const meta = await api("/api/meta");
  $("pairAddress").innerHTML = (meta.lan_ips?.length ? meta.lan_ips : ["127.0.0.1"]).map(ip => `<option>${esc(ip)}</option>`).join("");
  const update = () => {
    $("pairCodeImage").src = "/api/connect.png?address=" + encodeURIComponent($("pairAddress").value);
    $("pairCodeText").textContent = `电脑地址 ${$("pairAddress").value}:${meta.port} · 配对码 ${meta.pair_code || "请在电脑上打开教师页"}`;
  };
  $("pairAddress").onchange = update; update(); $("phonePairDialog").showModal();
};
$("closePhonePair").onclick = () => $("phonePairDialog").close();

$("reportSession").onchange = refreshReport;
$("reportClass").onchange = refreshReport;
$("resumeSession").onclick = async () => {
  const id = $("reportSession").value;
  if (!id) return;
  if (confirm("恢复所选课堂？当前课堂记录会保留。")) { await api("/api/sessions/resume", { id }); refreshState(); }
};
