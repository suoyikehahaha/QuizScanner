// Przybornik matematyczny edytora.
//
// Wzory wstawiamy jako zwykły tekst Unicode (√, ≤, π, x², H₂O, ½). Dzięki
// temu pytanie wygląda tak samo w edytorze, na tablicy, w eksporcie .quiz
// i w raporcie PDF — bez silnika LaTeX i bez żadnej biblioteki.
//
// ponytail: świadomie bez KaTeX/MathJax. Ułamki piętrowe i całki z granicami
// wymagałyby renderera; jeśli kiedyś będą potrzebne, wtedy dokładamy bibliotekę.

const MathBar = (() => {
  let target = null;          // ostatnie aktywne pole tekstowe

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

  // Szablony: {} oznacza miejsce, w którym ma stanąć kursor.
  const TEMPLATES = [
    { key: "mb_tpl_frac", text: "{}/" },
    { key: "mb_tpl_sqrt", text: "√({})" },
    { key: "mb_tpl_pow", text: "{}²" },
    { key: "mb_tpl_index", text: "{}₁" },
    { key: "mb_tpl_interval", text: "⟨{}; )" },
    { key: "mb_tpl_system", text: "{ {} " },
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
    const cursor = text.indexOf("{}");
    const clean = text.replace("{}", "");
    const start = target.selectionStart ?? target.value.length;
    const end = target.selectionEnd ?? start;
    const selected = target.value.slice(start, end);
    // Zaznaczony fragment wskakuje w miejsce {} — np. zaznacz "x+1" i kliknij √.
    const out = cursor >= 0 && selected ? text.replace("{}", selected) : clean;
    target.value = target.value.slice(0, start) + out + target.value.slice(end);
    const caret = start + (cursor >= 0 && !selected ? cursor : out.length);
    target.selectionStart = target.selectionEnd = caret;
    target.focus();
    target.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
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

    const hint = document.createElement("span");
    hint.className = "mb-hint";
    hint.textContent = t("mb_hint");

    box.append(tabs, keys, tools, hint);
    show(0);
  }

  return {
    // Podpina przybornik do kontenera i zaczyna śledzić aktywne pole.
    mount(box) {
      document.addEventListener("focusin", e => remember(e.target));
      render(box);
      document.addEventListener("i18n:changed", () => render(box));
    },
    insert,
  };
})();
