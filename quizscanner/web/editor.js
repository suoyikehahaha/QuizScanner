// Edytor quizów, ustawień i listy uczniów.
const LETTERS = ["A", "B", "C", "D"];
const $ = id => document.getElementById(id);
const MEDIA_MAX_MB = 40;

const DEFAULT_SETTINGS = {
  default_time: 20, default_points: 1000,
  shuffle_questions: false, shuffle_answers: false,
  show_distribution: true, auto_reveal_s: 6, auto_gap_s: 3,
};

function defaultSlide() {
  return { theme: "light", layout: "grid", size: "normal", option_size: "large" };
}

function normalizeSlide(slide) {
  const value = Object.assign(defaultSlide(), slide || {});
  const oldTheme = value.theme === "chinese-red" ? "chinese-paper" : value.theme;
  return {
    theme: ["night", "blue", "light", "chinese-paper", "ink", "jade", "chalkboard"].includes(oldTheme) ? oldTheme : "light",
    layout: ["grid", "list"].includes(value.layout) ? value.layout : "grid",
    size: ["small", "normal", "large"].includes(value.size) ? value.size : "normal",
    option_size: ["small", "normal", "large"].includes(value.option_size) ? value.option_size : "large",
  };
}

let quiz = { title: "", settings: Object.assign({}, DEFAULT_SETTINGS), questions: [] };
let currentName = null;
let mediaTargetIndex = null;   // do którego pytania wgrywamy plik

function esc(s) {
  return (s || "").replace(/[&<>"]/g, c => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
function toast(msg) {
  const el = $("toast"); el.textContent = msg; el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 1800);
}
async function api(path, body) {
  const opt = body ? { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body) } : {};
  return (await fetch(path, opt)).json();
}

// ---------- normalizacja ----------
function normalize(q) {
  q = q || {};
  return {
    title: q.title || "",
    settings: Object.assign({}, DEFAULT_SETTINGS, q.settings || {}),
    questions: (q.questions || []).map(x => ({
      text: x.text || "",
      material: x.material || "",
      source_number: x.source_number,
      answers: [0, 1, 2, 3].map(i => (x.answers && x.answers[i]) || ""),
      correct: (typeof x.correct === "number") ? x.correct : 0,
      time: x.time ?? 20,
      points: x.points ?? 1000,
      media: (x.media && x.media.file) ? { file: x.media.file, type: x.media.type || "image" } : null,
      slide: normalizeSlide(x.slide),
    })),
  };
}

// ---------- lista quizów ----------
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
    ul.innerHTML = `<li class="muted">${t("e_no_quizzes")}</li>`;
}

async function selectQuiz(name) {
  quiz = normalize(await api("/api/quiz?name=" + encodeURIComponent(name)));
  currentName = name;
  renderAll();
}

// ---------- render ----------
function renderAll() {
  $("quizTitle").value = quiz.title;
  $("editingName").textContent = currentName
    ? t("e_editing_file") + " " + currentName : t("e_unsaved");
  renderSettings();
  renderQuestions();
  loadQuizList();
}

function renderSettings() {
  const s = quiz.settings;
  $("setTime").value = s.default_time;
  $("setPoints").value = s.default_points;
  $("setReveal").value = s.auto_reveal_s;
  $("setGap").value = s.auto_gap_s;
  $("setShuffleQ").checked = !!s.shuffle_questions;
  $("setShuffleA").checked = !!s.shuffle_answers;
  $("setShowDist").checked = !!s.show_distribution;
}

function mediaRow(q, qi) {
  if (q.media && q.media.file) {
    const src = "/media/" + encodeURIComponent(q.media.file);
    const prev = q.media.type === "video"
      ? `<video src="${src}" class="mprev" muted></video>`
      : `<img src="${src}" class="mprev" alt="">`;
    return `<div class="media-row">${prev}
      <button class="btn-danger" data-act="media-del" data-qi="${qi}">${t("e_media_remove")}</button></div>`;
  }
  return `<div class="media-row">
    <button class="btn-ghost" data-act="media-add" data-qi="${qi}">${t("e_media_add")}</button>
    <span class="muted">${t("e_media_hint")}</span></div>`;
}

function slidePreview(q, qi) {
  const slide = normalizeSlide(q.slide);
  const mediaSrc = q.media && q.media.file ? "/media/" + encodeURIComponent(q.media.file) : "";
  const media = !mediaSrc ? "" : q.media.type === "video"
    ? `<video class="slide-preview-media" src="${mediaSrc}" muted loop autoplay playsinline></video>`
    : `<img class="slide-preview-media" src="${mediaSrc}" alt="">`;
  return `<div class="slide-preview" data-qi="${qi}" data-theme="${slide.theme}" data-layout="${slide.layout}" data-size="${slide.size}" data-option-size="${slide.option_size}">
    <div class="slide-preview-top"><span>${esc(quiz.title || t("e_quiz_title_ph"))}</span><b>${t("e_question_n", { n: qi + 1 })}</b></div>
    <div class="slide-preview-question">${q.text ? tex(q.text) : `<span class="slide-preview-empty">${t("e_question_ph")}</span>`}</div>
    ${media}
    <div class="slide-preview-answers">${q.answers.map((answer, i) => `
      <div class="slide-preview-option opt-${LETTERS[i]}"><span>${LETTERS[i]}</span><b>${answer ? tex(answer) : "…"}</b></div>`).join("")}</div>
    <div class="slide-preview-foot">${t("e_preview_ratio")}</div>
  </div>`;
}

function renderQuestions() {
  const box = $("questions"); box.innerHTML = "";
  quiz.questions.forEach((q, qi) => {
    q.slide = normalizeSlide(q.slide);
    const card = document.createElement("div");
    card.className = "qcard";
    card.dataset.qi = qi;
    card.innerHTML = `
      <div class="qrow">
        <span class="qnum">${t("e_question_n", { n: qi + 1 })}</span>
        <div class="qtools">
          <button class="btn-ghost" data-act="up" data-qi="${qi}">▲</button>
          <button class="btn-ghost" data-act="down" data-qi="${qi}">▼</button>
          <button class="btn-danger" data-act="del" data-qi="${qi}">🗑</button>
        </div>
      </div>
      <div class="qslide-editor">
        <div class="qfields">
          <label class="field">阅读材料（可留空，投影时单独展开）</label>
          <textarea class="text q-material" data-qi="${qi}" placeholder="粘贴阅读材料，同一材料可以用于多道子题">${esc(q.material || "")}</textarea>
          <label class="field">题干 · 可使用 **重点** 加粗、==重点== 标记</label>
          <textarea class="text q-text" data-qi="${qi}" placeholder="${t("e_question_ph")}">${esc(q.text)}</textarea>
          <label class="field mt">${t("e_media")}</label>
          ${mediaRow(q, qi)}
          <div class="opts-ed">
            ${[0, 1, 2, 3].map(ai => `
              <div class="opt-ed opt-${LETTERS[ai]}">
                <span class="badge">${LETTERS[ai]}</span>
                <input class="text q-ans" data-qi="${qi}" data-ai="${ai}"
                       placeholder="${t("e_answer_ph", { letter: LETTERS[ai] })}" value="${esc(q.answers[ai])}">
                <label class="pick"><input type="radio" name="correct-${qi}" value="${ai}"
                       ${q.correct === ai ? "checked" : ""}> ${t("e_correct")}</label>
              </div>`).join("")}
          </div>
          <div class="meta-row">
            <div class="m"><label class="field">${t("e_time_s")}</label>
              <input class="text q-time" type="number" min="0" data-qi="${qi}" value="${q.time}"></div>
            <div class="m"><label class="field">${t("e_points")}</label>
              <input class="text q-points" type="number" min="0" step="100" data-qi="${qi}" value="${q.points}"></div>
          </div>
          <div class="slide-controls">
            <b>${t("e_slide_design")}</b>
            <label><span>${t("e_slide_theme")}</span><select class="q-slide-theme" data-qi="${qi}">
              <option value="night" ${q.slide.theme === "night" ? "selected" : ""}>${t("e_slide_night")}</option>
              <option value="blue" ${q.slide.theme === "blue" ? "selected" : ""}>${t("e_slide_blue")}</option>
              <option value="light" ${q.slide.theme === "light" ? "selected" : ""}>${t("e_slide_light")}</option>
              <option value="chinese-paper" ${q.slide.theme === "chinese-paper" ? "selected" : ""}>${t("e_slide_chinese_paper")}</option>
              <option value="ink" ${q.slide.theme === "ink" ? "selected" : ""}>${t("e_slide_ink")}</option>
              <option value="jade" ${q.slide.theme === "jade" ? "selected" : ""}>${t("e_slide_jade")}</option>
              <option value="chalkboard" ${q.slide.theme === "chalkboard" ? "selected" : ""}>${t("e_slide_chalkboard")}</option>
            </select></label>
            <label><span>${t("e_slide_layout")}</span><select class="q-slide-layout" data-qi="${qi}">
              <option value="grid" ${q.slide.layout === "grid" ? "selected" : ""}>${t("e_slide_grid")}</option>
              <option value="list" ${q.slide.layout === "list" ? "selected" : ""}>${t("e_slide_list")}</option>
            </select></label>
            <label><span>${t("e_slide_size")}</span><select class="q-slide-size" data-qi="${qi}">
              <option value="small" ${q.slide.size === "small" ? "selected" : ""}>${t("e_slide_size_small")}</option>
              <option value="normal" ${q.slide.size === "normal" ? "selected" : ""}>${t("e_slide_size_normal")}</option>
              <option value="large" ${q.slide.size === "large" ? "selected" : ""}>${t("e_slide_size_large")}</option>
            </select></label>
            <label><span>${t("e_slide_option_size")}</span><select class="q-slide-option-size" data-qi="${qi}">
              <option value="small" ${q.slide.option_size === "small" ? "selected" : ""}>${t("e_slide_option_size_small")}</option>
              <option value="normal" ${q.slide.option_size === "normal" ? "selected" : ""}>${t("e_slide_option_size_normal")}</option>
              <option value="large" ${q.slide.option_size === "large" ? "selected" : ""}>${t("e_slide_option_size_large")}</option>
            </select></label>
          </div>
        </div>
        <div class="slide-preview-column">
          <div class="slide-preview-label">${t("e_preview_ratio")} <button class="btn-ghost" data-act="project-preview" data-qi="${qi}">大屏预览</button><span class="preview-warning" id="overflow-${qi}"></span></div>
          ${slidePreview(q, qi)}
        </div>
      </div>`;
    box.appendChild(card);
  });

  box.querySelectorAll("button[data-act]").forEach(b => {
    b.onclick = () => {
      syncFromDom();
      const qi = +b.dataset.qi, act = b.dataset.act;
      if (act === "del") quiz.questions.splice(qi, 1);
      else if (act === "up" && qi > 0)
        [quiz.questions[qi - 1], quiz.questions[qi]] = [quiz.questions[qi], quiz.questions[qi - 1]];
      else if (act === "down" && qi < quiz.questions.length - 1)
        [quiz.questions[qi + 1], quiz.questions[qi]] = [quiz.questions[qi], quiz.questions[qi + 1]];
      else if (act === "project-preview") {
        syncFromDom();
        const key = "quizscanner.preview." + Date.now();
        sessionStorage.setItem(key, JSON.stringify({ quiz_title: quiz.title, index: qi, total: quiz.questions.length,
          phase: "question", question: quiz.questions[qi], active_class: "预览", roster_total: 0,
          distribution: { A: 0, B: 0, C: 0, D: 0 }, answered: 0, live_students: [] }));
        const dialog = document.createElement("dialog");
        dialog.className = "projection-preview-dialog";
        dialog.innerHTML = `<button class="btn-primary">关闭预览</button><iframe title="投影大屏预览" src="/board?preview=${encodeURIComponent(key)}"></iframe>`;
        document.body.appendChild(dialog); dialog.showModal();
        dialog.querySelector("button").onclick = () => { dialog.close(); dialog.remove(); sessionStorage.removeItem(key); };
        return;
      }
      else if (act === "media-add") { mediaTargetIndex = qi; $("mediaFile").click(); return; }
      else if (act === "media-del") quiz.questions[qi].media = null;
      renderQuestions();
    };
  });
  box.querySelectorAll(".q-text, .q-material, .q-ans, .q-time, .q-points").forEach(el => {
    el.addEventListener("input", () => {
      syncFromDom();
      refreshSlidePreview(+el.dataset.qi);
    });
  });
  box.querySelectorAll(".q-slide-theme, .q-slide-layout, .q-slide-size, .q-slide-option-size").forEach(el => {
    el.addEventListener("change", () => {
      syncFromDom();
      refreshSlidePreview(+el.dataset.qi);
    });
  });
}

function refreshSlidePreview(qi) {
  const preview = document.querySelector(`.slide-preview[data-qi="${qi}"]`);
  if (preview && quiz.questions[qi]) preview.outerHTML = slidePreview(quiz.questions[qi], qi);
  const warning = $("overflow-" + qi);
  if (warning) warning.textContent = (quiz.questions[qi].text.length > 160 || quiz.questions[qi].answers.some(a => a.length > 65))
    ? "内容较长，请用大屏预览检查字号与完整显示" : "";
}

function syncFromDom() {
  quiz.title = $("quizTitle").value;
  document.querySelectorAll(".q-material").forEach(el => quiz.questions[+el.dataset.qi].material = el.value);
  document.querySelectorAll(".q-text").forEach(el => quiz.questions[+el.dataset.qi].text = el.value);
  document.querySelectorAll(".q-ans").forEach(el => quiz.questions[+el.dataset.qi].answers[+el.dataset.ai] = el.value);
  document.querySelectorAll(".q-time").forEach(el => quiz.questions[+el.dataset.qi].time = +el.value || 0);
  document.querySelectorAll(".q-points").forEach(el => quiz.questions[+el.dataset.qi].points = +el.value || 0);
  document.querySelectorAll(".q-slide-theme").forEach(el => quiz.questions[+el.dataset.qi].slide.theme = el.value);
  document.querySelectorAll(".q-slide-layout").forEach(el => quiz.questions[+el.dataset.qi].slide.layout = el.value);
  document.querySelectorAll(".q-slide-size").forEach(el => quiz.questions[+el.dataset.qi].slide.size = el.value);
  document.querySelectorAll(".q-slide-option-size").forEach(el => quiz.questions[+el.dataset.qi].slide.option_size = el.value);
  document.querySelectorAll('input[type=radio]:checked').forEach(el => {
    const qi = +el.name.split("-")[1]; quiz.questions[qi].correct = +el.value;
  });
  quiz.settings = {
    default_time: +$("setTime").value || 0,
    default_points: +$("setPoints").value || 0,
    auto_reveal_s: +$("setReveal").value || 0,
    auto_gap_s: +$("setGap").value || 0,
    shuffle_questions: $("setShuffleQ").checked,
    shuffle_answers: $("setShuffleA").checked,
    show_distribution: $("setShowDist").checked,
  };
}

// ---------- media ----------
$("mediaFile").onchange = async () => {
  const f = $("mediaFile").files[0];
  $("mediaFile").value = "";
  if (!f || mediaTargetIndex == null) return;
  if (f.size > MEDIA_MAX_MB * 1024 * 1024) { toast(t("e_media_too_big", { mb: MEDIA_MAX_MB })); return; }
  const dataUrl = await new Promise(res => {
    const fr = new FileReader(); fr.onload = () => res(fr.result); fr.readAsDataURL(f);
  });
  const r = await api("/api/media", { data: dataUrl, name: f.name });
  if (!r.ok) { toast(t("e_media_bad_type")); return; }
  syncFromDom();
  quiz.questions[mediaTargetIndex].media = { file: r.file, type: r.type };
  mediaTargetIndex = null;
  renderQuestions();
};

// ---------- akcje quizu ----------
$("addQ").onclick = () => {
  syncFromDom();
  const s = quiz.settings;
  quiz.questions.push({
    text: "", answers: ["", "", "", ""], correct: 0,
    time: s.default_time, points: s.default_points, media: null, slide: defaultSlide(),
  });
  renderQuestions();
};
$("applyAll").onclick = () => {
  syncFromDom();
  quiz.questions.forEach(q => {
    q.time = quiz.settings.default_time;
    q.points = quiz.settings.default_points;
  });
  renderQuestions(); toast(t("s_applied"));
};
$("newQuiz").onclick = () => {
  quiz = { title: "", settings: Object.assign({}, DEFAULT_SETTINGS), questions: [] };
  currentName = null; renderAll();
};
$("saveQuiz").onclick = async () => {
  syncFromDom();
  const r = await api("/api/quiz", { name: currentName || (quiz.title || "quiz"), quiz });
  currentName = r.name; renderAll(); toast(t("e_saved") + " " + r.name);
};
$("dupQuiz").onclick = async () => {
  syncFromDom();
  const r = await api("/api/quiz", { name: (quiz.title || "quiz") + " kopia", quiz });
  currentName = r.name; renderAll(); toast(t("e_copy_made") + " " + r.name);
};
$("delQuiz").onclick = async () => {
  if (!currentName) { $("newQuiz").onclick(); return; }
  if (!confirm(t("e_confirm_delete", { name: currentName }))) return;
  await api("/api/quiz/delete", { name: currentName });
  currentName = null; $("newQuiz").onclick(); toast(t("e_deleted"));
};

// zapis do pliku / wczytanie z pliku (dzielenie się quizem)
$("exportQuiz").onclick = async () => {
  syncFromDom();
  const name = currentName || (quiz.title || "quiz");
  await api("/api/quiz", { name, quiz });     // najpierw zapisz bieżący stan
  currentName = name; renderAll();
  window.open("/api/quiz/export?name=" + encodeURIComponent(name), "_blank");
};
$("importBtn").onclick = () => $("importFile").click();
$("importFile").onchange = async () => {
  const f = $("importFile").files[0];
  $("importFile").value = "";
  if (!f) return;
  try {
    const bundle = JSON.parse(await f.text());
    if (!bundle || !Array.isArray(bundle.questions)) throw new Error("bad");
    const base = (f.name || "quiz").replace(/\.(quiz|json)$/i, "");
    const r = await api("/api/quiz/import", { name: bundle.title || base, quiz: bundle });
    if (!r.ok) throw new Error("bad");
    await selectQuiz(r.name);
    toast(t("e_imported"));
  } catch (e) { toast(t("e_import_failed")); }
};

$("importDocxBtn").onclick = () => $("importDocxFile").click();
$("importDocxFile").onchange = async () => {
  const file = $("importDocxFile").files[0];
  $("importDocxFile").value = "";
  if (!file) return;
  if (file.size > 8 * 1024 * 1024) { toast(t("e_docx_too_big")); return; }
  try {
    const content = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error("file"));
      reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
      reader.readAsDataURL(file);
    });
    const result = await api("/api/quiz/import-docx", {
      filename: file.name, content_base64: content,
    });
    if (!result.ok) throw new Error(result.error || "parse");
    if (!confirm(t("e_docx_replace"))) return;
    quiz = normalize(result.quiz);
    currentName = null;
    renderAll();
    toast(t("e_docx_result", {
      count: result.question_count,
      missing: result.missing_answers,
    }));
  } catch (error) {
    toast(`${t("e_docx_failed")}: ${error.message}`);
  }
};

$("toTeacher").onclick = () => location.href = "/teacher";

// ---------- zakładki ----------
$("tabQuiz").onclick = () => switchTab("quiz");
$("tabRoster").onclick = () => switchTab("roster");
function switchTab(tab) {
  $("tabQuiz").classList.toggle("active", tab === "quiz");
  $("tabRoster").classList.toggle("active", tab === "roster");
  $("quizView").classList.toggle("hidden", tab !== "quiz");
  $("rosterView").classList.toggle("hidden", tab !== "roster");
  if (tab === "roster") loadRoster();
}

// ---------- uczniowie ----------
let roster = { version: 2, classes: [], active_class: "", students: [] };
async function loadRoster() {
  roster = await api("/api/roster");
  renderRoster();
}
function rosterClasses() {
  const classes = new Set((roster.classes || []).map(className => String(className || "").trim())
    .filter(Boolean));
  (roster.students || []).forEach(student => {
    classes.add(String(student.class_name || "未分班").trim() || "未分班");
  });
  return [...classes].sort((a, b) => a.localeCompare(b, "zh-CN", { numeric: true }));
}
function renderRoster() {
  const body = $("rosterBody");
  body.innerHTML = "";
  roster.students = (roster.students || []).slice().sort((a, b) =>
    String(a.class_name || "").localeCompare(String(b.class_name || ""), "zh-CN", { numeric: true }) ||
    String(a.student_no || "").localeCompare(String(b.student_no || ""), "zh-CN", { numeric: true })
  );
  roster.students.forEach((student, index) => {
    const tr = document.createElement("tr");
    tr.dataset.index = String(index);
    tr.innerHTML =
      '<td><input class="text r-no" value="' + esc(student.student_no || "") + '" style="width:110px"></td>' +
      '<td><input class="text r-class" value="' + esc(student.class_name || "未分班") + '" style="width:130px"></td>' +
      '<td><input class="text r-name" value="' + esc(student.name || "") + '"></td>' +
      '<td><input class="text r-card" type="number" min="0" max="249" value="' + esc(student.card_id == null ? "" : String(student.card_id)) + '" style="width:70px"></td>' +
      '<td><button class="btn-danger r-del">✕</button></td>';
    tr.querySelector(".r-del").onclick = () => {
      syncRoster();
      roster.students.splice(index, 1);
      renderRoster();
    };
    body.appendChild(tr);
  });
  const select = $("rosterClass");
  const classes = rosterClasses();
  roster.classes = classes.slice();
  select.replaceChildren();
  if (classes.length) {
    if (!classes.includes(roster.active_class)) roster.active_class = classes[0];
    classes.forEach(className => {
      const option = document.createElement("option");
      option.value = className;
      option.textContent = className;
      option.selected = className === roster.active_class;
      select.appendChild(option);
    });
  } else {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = t("e_select_class");
    select.appendChild(option);
    roster.active_class = "";
  }
  select.onchange = async () => {
    syncRoster();
    roster.active_class = select.value;
    if (!roster.active_class) return;
    try {
      const result = await api("/api/roster/class", { class_name: roster.active_class });
      if (!result.ok) throw new Error(result.error || "无法切换作答班级");
    } catch (error) {
      toast(error.message);
    }
  };
}
function syncRoster() {
  const students = [];
  document.querySelectorAll("#rosterBody tr").forEach(tr => {
    const student_no = tr.querySelector(".r-no").value.trim();
    const class_name = tr.querySelector(".r-class").value.trim() || "未分班";
    const name = tr.querySelector(".r-name").value.trim();
    const card_id = tr.querySelector(".r-card").value;
    if (student_no || name) {
      students.push({
        student_no: student_no || name,
        class_name,
        name,
        card_id: card_id === "" ? null : Number(card_id),
      });
    }
  });
  roster.students = students;
  roster.classes = rosterClasses();
}

$("createClass").onclick = async () => {
  const className = $("newClassName").value.trim();
  if (!className) { toast(t("e_class_name_required")); return; }
  syncRoster();
  const classes = rosterClasses();
  if (classes.includes(className)) { toast(t("e_class_duplicate")); return; }
  const localStudents = roster.students.slice();
  try {
    const result = await api("/api/roster/class/create", { class_name: className });
    if (!result.ok) throw new Error(result.error || t("e_upload_failed"));
    const saved = result.roster || { classes: [], students: [] };
    roster = {
      ...saved,
      students: localStudents,
      classes: [...new Set([...(saved.classes || []), ...classes, className])],
      active_class: className,
    };
    $("newClassName").value = "";
    renderRoster();
    toast(t("e_create_class_success", { name: className }));
  } catch (error) {
    toast(error.message);
  }
};
$("newClassName").addEventListener("keydown", event => {
  if (event.key === "Enter") { event.preventDefault(); $("createClass").click(); }
});

$("addStudent").onclick = () => {
  syncRoster();
  const className = $("rosterClass").value || roster.active_class;
  if (!className) { toast(t("e_class_required")); return; }
  roster.students.push({
    student_no: "",
    class_name: className,
    name: "",
    card_id: null,
  });
  renderRoster();
};
$("rosterFile").onchange = async event => {
  const file = event.target.files && event.target.files[0];
  if (!file) return;
  try {
    if (file.size > 3 * 1024 * 1024) throw new Error(t("e_upload_too_big"));
    syncRoster();
    const targetClass = $("rosterClass").value || roster.active_class;
    if (!targetClass) throw new Error(t("e_class_required"));
    const contentBase64 = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error(t("e_upload_failed")));
      reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
      reader.readAsDataURL(file);
    });
    const result = await api("/api/roster/import", {
      filename: file.name,
      content_base64: contentBase64,
      class_name: targetClass,
    });
    if (!result.ok) throw new Error(result.error || t("e_upload_failed"));
    const imported = result.roster || { classes: [], students: [] };
    const importedStudents = imported.students || [];
    const importedClasses = new Set([...(imported.classes || []),
      ...importedStudents.map(student => student.class_name).filter(Boolean)]);
    const replaces = roster.students.filter(student => importedClasses.has(student.class_name));
    if (replaces.length && !confirm(t("e_upload_confirm", {
      classes: [...importedClasses].join(", "), count: replaces.length,
    }))) return;
    roster.students = roster.students.filter(student => !importedClasses.has(student.class_name))
      .concat(importedStudents);
    roster.classes = [...new Set([...rosterClasses(), ...importedClasses])];
    roster.active_class = targetClass;
    renderRoster();
    toast(t("e_upload_success", { count: result.count }));
  } catch (error) {
    toast(t("e_upload_failed") + ": " + error.message);
  } finally {
    event.target.value = "";
  }
};
$("saveRoster").onclick = async () => {
  try {
    syncRoster();
    const result = await api("/api/roster", roster);
    if (!result.ok) throw new Error(result.error || t("e_upload_failed"));
    roster = result.roster || roster;
    renderRoster();
    toast(t("e_roster_saved"));
  } catch (error) {
    toast(error.message);
  }
};
$("cardsBtn").onclick = async () => {
  try {
    syncRoster();
    const className = $("rosterClass").value || roster.active_class;
    if (!className || !roster.students.some(student => student.class_name === className)) {
      toast(t("e_add_students_first")); return;
    }
    roster.active_class = className;
    const result = await api("/api/roster", roster);
    if (!result.ok) throw new Error(result.error || t("e_upload_failed"));
    roster = result.roster || roster;
    toast(t("e_generating_pdf"));
    window.open("/api/cards.pdf?class=" + encodeURIComponent(className), "_blank");
  } catch (error) {
    toast(error.message);
  }
};

// ---------- język i motyw ----------
$("langSel").onchange = async () => {
  await api("/api/settings", { lang: $("langSel").value });
  setLang($("langSel").value);
};
$("themeSel").onchange = async () => {
  setTheme($("themeSel").value);
  await api("/api/settings", { theme: $("themeSel").value });
};
document.addEventListener("i18n:changed", () => {
  fillThemeSelect($("themeSel"));
  if (quiz) renderAll();
});

// ---------- przybornik matematyczny ----------
$("mathToggle").onclick = () => {
  const on = $("mathPanel").classList.toggle("collapsed");
  $("mathToggle").textContent = t(on ? "mb_show" : "mb_hide");
};

$("quizTitle").addEventListener("input", () => {
  syncFromDom();
  quiz.questions.forEach((_, qi) => refreshSlidePreview(qi));
});

// ---------- start ----------
(async function init() {
  await initLang();
  fillThemeSelect($("themeSel"));
  $("themeSel").value = document.documentElement.dataset.theme || "dark";
  MathBar.mount($("mathBox"));
  $("langSel").value = document.documentElement.lang;
  const r = await api("/api/quizzes");
  if (r.quizzes && r.quizzes.length) await selectQuiz(r.active || r.quizzes[0]);
  else { quiz = normalize({ title: "" }); renderAll(); }
})();
