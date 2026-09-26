// Pair remote browser teacher tools while keeping the local desktop workflow.
(() => {
  const original = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const url = new URL(typeof input === "string" ? input : input.url, location.href);
    if (url.origin !== location.origin || !url.pathname.startsWith("/api/")) return original(input, init);
    const options = { ...init, headers: new Headers(init.headers || {}) };
    const token = sessionStorage.getItem("quizscanner.teacher-token");
    if (token) options.headers.set("X-Teacher-Token", token);
    const response = await original(input, options);
    if (response.status !== 401) return response;
    const code = prompt("请输入电脑教师页“手机扫码连接”中显示的六位配对码。");
    if (!code) return response;
    const paired = await original("/api/native/pair", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code }) });
    if (!paired.ok) return response;
    const result = await paired.json();
    sessionStorage.setItem("quizscanner.teacher-token", result.token);
    options.headers.set("X-Teacher-Token", result.token);
    return original(input, options);
  };
})();
