// Przybornik matematyczny edytora — dwie drogi zapisu wzoru:
//
//  1. Symbole Unicode (√, ≤, π, x², H₂O, ½) — zwykły tekst, wygląda tak samo
//     wszędzie: w edytorze, na tablicy, w pliku .quiz i w raporcie.
//  2. LaTeX w dolarach ($\frac{1}{2}$) — renderowany przez KaTeX na tablicy
//     i w panelu. Do ułamków piętrowych, całek z granicami, macierzy i układów
//     równań, których Unicode nie zapisze.
//
// Podgląd pod przybornikiem pokazuje na żywo, jak wygląda pole, które właśnie
// edytujesz — także wtedy, gdy siedzi w nim mieszanka tekstu i wzorów.

const MathBar = (() => {
  let target = null;          // ostatnie aktywne pole tekstowe
  let preview = null;         // element podglądu (renderowany przez KaTeX)

  // Znacznik miejsca na kursor w szablonie. Nie może to być "{}", bo nawiasy
  // klamrowe są częścią składni LaTeX-a (\frac{}{}).
  const CARET = "‸";

  const GROUPS = [
    { key: "mb_basic", items: [
      "+", "−", "×", "÷", "±", "∓", "·", "=", "≠", "≈", "≡", "<", ">", "≤", "≥",
      "%", "‰", "∞", "°", "′", "″"] },
    { key: "mb_powers", items: [
      "²", "³", "⁴", "ⁿ", "⁻¹", "₀", "₁", "₂", "₃", "ₙ", "√", "∛", "ⁿ√",
      "½", "⅓", "¼", "¾", "⅔", "⅜", "/", "⁄"] },
    { key: "mb_greek", items: [
      "α", "β", "γ", "δ", "ε", "θ", "λ", "μ", "π", "ρ", "σ", "τ", "φ", "ω",
      "Δ", "Σ", "Π", "Ω", "Θ", "Λ"] },
    { key: "mb_sets", items: [
      "∈", "∉", "⊂", "⊆", "⊄", "∪", "∩", "∅", "∀", "∃", "¬", "∧", "∨", "⇒",
      "⇔", "→", "↔", "ℕ", "ℤ", "ℚ", "ℝ", "ℂ"] },
    { key: "mb_geo", items: [
      "∠", "⊥", "∥", "△", "□", "○", "≅", "∼", "⌀", "→", "↑", "↓", "↗", "∆"] },
    { key: "mb_calc", items: [
      "∑", "∏", "∫", "∬", "∮", "∂", "∇", "lim", "log", "ln",
      "sin", "cos", "tg", "ctg", "!", "≐", "∝"] },   // polish-ok (cos = cosinus)
  ];

  // Szablony Unicode: CARET oznacza miejsce, w którym ma stanąć kursor.
  const TEMPLATES = [
    { key: "mb_tpl_frac", text: CARET + "/" },
    { key: "mb_tpl_sqrt", text: "√(" + CARET + ")" },
    { key: "mb_tpl_pow", text: CARET + "²" },
    { key: "mb_tpl_index", text: CARET + "₁" },
    { key: "mb_tpl_interval", text: "⟨" + CARET + "; )" },
  ];

  // Szablony LaTeX — wstawiane razem z dolarami, żeby od razu się renderowały.
  const TEX_TEMPLATES = [
    { label: "$…$", key: "mb_tex_inline", text: "$" + CARET + "$" },
    { label: "a⁄b", key: "mb_tex_frac", text: "$\\frac{" + CARET + "}{ }$" },
    { label: "√", key: "mb_tex_sqrt", text: "$\\sqrt{" + CARET + "}$" },
    { label: "ⁿ√", key: "mb_tex_root", text: "$\\sqrt[n]{" + CARET + "}$" },
    { label: "xⁿ", key: "mb_tex_pow", text: "$" + CARET + "^{ }$" },
    { label: "xₙ", key: "mb_tex_sub", text: "$" + CARET + "_{ }$" },
    { label: "∫", key: "mb_tex_int", text: "$\\int_{a}^{b} " + CARET + " \\,dx$" },
    { label: "∑", key: "mb_tex_sum", text: "$\\sum_{i=1}^{n} " + CARET + "$" },
    { label: "lim", key: "mb_tex_lim", text: "$\\lim_{x \\to 0} " + CARET + "$" },
    { label: "(ⁿₖ)", key: "mb_tex_binom", text: "$\\binom{n}{k}$" },
    { label: "x̄", key: "mb_tex_bar", text: "$\\overline{" + CARET + "}$" },
    { label: "v⃗", key: "mb_tex_vec", text: "$\\vec{" + CARET + "}$" },
    { label: "{ ⋮", key: "mb_tex_cases",
      text: "$\\begin{cases} " + CARET + " \\\\ \\end{cases}$" },
    { label: "[ ⋱ ]", key: "mb_tex_matrix",
      text: "$\\begin{pmatrix} " + CARET + " & \\\\ & \\end{pmatrix}$" },
    { label: "$$…$$", key: "mb_tex_block", text: "$$" + CARET + "$$" },
  ];

  const SUP = { "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵",
                "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "+": "⁺", "-": "⁻",
                "n": "ⁿ", "i": "ⁱ", "(": "⁽", ")": "⁾" };
  const SUB = { "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅",
                "6": "₆", "7": "₇", "8": "₈", "9": "₉", "+": "₊", "-": "₋",
                "n": "ₙ", "a": "ₐ", "(": "₍", ")": "₎" };

  function map(text, table) {
    return [...text].map(c => table[c] || c).join("");
  }

  // Pola edytora są przerysowywane przy każdej zmianie, więc trzymamy się
  // ostatniego pola, w którym stał kursor.
  function remember(el) {
    if (el && (el.tagName === "TEXTAREA" ||
               (el.tagName === "INPUT" && el.type === "text"))) target = el;
  }

  function insert(text) {
    if (!target || !document.body.contains(target)) return false;
    const cursor = text.indexOf(CARET);
    const clean = text.replace(CARET, "");
    const start = target.selectionStart ?? target.value.length;
    const end = target.selectionEnd ?? start;
    const selected = target.value.slice(start, end);
    // Zaznaczony fragment wskakuje w miejsce kursora — np. zaznacz "x+1"
    // i kliknij √, żeby dostać √(x+1) albo $\sqrt{x+1}$.
    const out = cursor >= 0 && selected ? text.replace(CARET, selected) : clean;
    target.value = target.value.slice(0, start) + out + target.value.slice(end);
    const caret = start + (cursor >= 0 && !selected ? cursor : out.length);
    target.selectionStart = target.selectionEnd = caret;
    target.focus();
    target.dispatchEvent(new Event("input", { bubbles: true }));
    refreshPreview();
    return true;
  }

  // Podgląd tego, co widzą uczniowie — pole edytowane właśnie teraz.
  function refreshPreview() {
    if (!preview) return;
    const value = target ? target.value : "";
    preview.innerHTML = value.trim()
      ? TeX.render(value)
      : `<span class="muted">${TeX.esc(t("mb_preview_empty"))}</span>`;
  }

  function convertSelection(table) {
    if (!target) return;
    const start = target.selectionStart, end = target.selectionEnd;
    if (start === end) return;
    insert(map(target.value.slice(start, end), table));
  }

  function button(label, title, onClick) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "mb-key";
    b.textContent = label;
    b.title = title || label;
    // mousedown zamiast click: nie zabieramy fokusu polu tekstowemu.
    b.addEventListener("mousedown", e => { e.preventDefault(); onClick(); });
    return b;
  }

  function render(box) {
    box.innerHTML = "";
    const tabs = document.createElement("div");
    tabs.className = "mb-tabs";
    const keys = document.createElement("div");
    keys.className = "mb-keys";

    const show = i => {
      keys.innerHTML = "";
      GROUPS[i].items.forEach(sym => keys.appendChild(
        button(sym, sym, () => insert(sym))));
      [...tabs.children].forEach((el, n) => el.classList.toggle("active", n === i));
    };
    GROUPS.forEach((g, i) => {
      const b = button(t(g.key), t(g.key), () => show(i));
      b.className = "mb-tab";
      tabs.appendChild(b);
    });

    const tools = document.createElement("div");
    tools.className = "mb-tools";
    TEMPLATES.forEach(tpl => tools.appendChild(
      button(t(tpl.key), t(tpl.key), () => insert(tpl.text))));
    tools.appendChild(button("x²", t("mb_to_sup"), () => convertSelection(SUP)));
    tools.appendChild(button("x₂", t("mb_to_sub"), () => convertSelection(SUB)));

    // Sekcja LaTeX — dla wzorów, których Unicode nie zapisze.
    const texRow = document.createElement("div");
    texRow.className = "mb-tex";
    const texLabel = document.createElement("span");
    texLabel.className = "mb-tex-label";
    texLabel.textContent = t("mb_tex_title");
    texRow.appendChild(texLabel);
    TEX_TEMPLATES.forEach(tpl => texRow.appendChild(
      button(tpl.label, t(tpl.key), () => insert(tpl.text))));

    const hint = document.createElement("span");
    hint.className = "mb-hint";
    hint.textContent = t("mb_hint");

    const previewWrap = document.createElement("div");
    previewWrap.className = "mb-preview";
    previewWrap.innerHTML = `<span class="field">${TeX.esc(t("mb_preview"))}</span>`;
    preview = document.createElement("div");
    preview.className = "mb-preview-out";
    previewWrap.appendChild(preview);

    box.append(tabs, keys, tools, texRow, hint, previewWrap);
    show(0);
    refreshPreview();
  }

  return {
    // Podpina przybornik do kontenera i zaczyna śledzić aktywne pole.
    mount(box) {
      document.addEventListener("focusin", e => {
        remember(e.target);
        refreshPreview();
      });
      // Podgląd nadąża za pisaniem w polu pytania i odpowiedzi.
      document.addEventListener("input", e => {
        if (e.target === target) refreshPreview();
      });
      render(box);
      document.addEventListener("i18n:changed", () => render(box));
    },
    insert,
  };
})();
