// Renderowanie wzorów LaTeX w treści pytań i odpowiedzi.
//
// Wzór zamykamy w dolarach:  Pole koła to $\pi r^2$, a przekątna $\sqrt{2}$.
// Podwójne dolary dają wzór wyśrodkowany w osobnej linii:  $$\int_0^1 x\,dx$$
//
// Poza dolarami tekst zostaje zwykłym tekstem i jest escapowany — dzięki temu
// ta sama funkcja bezpiecznie zastępuje esc() w widokach.
//
// KaTeX leży w web/vendor/katex (offline, bez CDN). Gdy z jakiegoś powodu się
// nie wczyta, pokazujemy surowy zapis wzoru zamiast pustego miejsca.

const TeX = (() => {
  // $$...$$ (wyśrodkowany) albo $...$ (w linii). \$ to zwykły znak dolara.
  const RE = /\$\$([\s\S]+?)\$\$|(?<!\\)\$([^$\n]+?)(?<!\\)\$/g;

  function esc(s) {
    return (s == null ? "" : String(s)).replace(/[&<>"]/g, c => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  // Fragment poza wzorem: escapujemy i zwalniamy \$ do zwykłego dolara.
  function plain(s) {
    return esc(s).replace(/\\\$/g, "$");
  }

  function one(code, display) {
    if (typeof katex === "undefined") return esc(code);
    try {
      return katex.renderToString(code, {
        displayMode: display, throwOnError: false, output: "html",
        strict: false, trust: false,
      });
    } catch (e) {
      return `<span class="tex-error">${esc(code)}</span>`;
    }
  }

  return {
    // Czy w tekście w ogóle jest wzór (do decyzji "pokazać podgląd?").
    has(text) { RE.lastIndex = 0; return RE.test(String(text || "")); },

    // Tekst -> bezpieczny HTML ze wzorami. Zastępuje esc() tam, gdzie
    // dopuszczamy wzory (tablica, panel, podgląd w edytorze).
    render(text) {
      text = text == null ? "" : String(text);
      let out = "", last = 0, m;
      RE.lastIndex = 0;
      while ((m = RE.exec(text)) !== null) {
        out += plain(text.slice(last, m.index));
        out += m[1] !== undefined ? one(m[1], true) : one(m[2], false);
        last = m.index + m[0].length;
      }
      return out + plain(text.slice(last));
    },
    esc,
  };
})();

// Skrót używany w widokach.
const tex = t => TeX.render(t);
