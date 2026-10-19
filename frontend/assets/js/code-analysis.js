(async function () {
  const { el } = UI;
  const { main } = Layout.init({ page: "code" });
  const MAX_BYTES = 50000;
  const history = el("div");

  const filename = el("input", { id: "filename", value: "snippet.py", maxlength: 100 });
  const code = el("textarea", { id: "code", class: "code", spellcheck: "false", placeholder: "Paste Python code here…" });
  const counter = el("span", { class: "muted small" }, "0 bytes");
  const banner = el("div", { class: "form-error", role: "alert" });
  const taskSel = el("select", { id: "task" }, el("option", { value: "" }, "— not linked to a task —"));
  const submit = el("button", { class: "btn primary", type: "submit" }, "Analyze code");
  code.addEventListener("input", () => { const n = new Blob([code.value]).size; counter.textContent = `${n} / ${MAX_BYTES} bytes`; counter.className = n > MAX_BYTES ? "overdue small" : "muted small"; });
  const file = el("input", { type: "file", accept: ".py,text/x-python,text/plain", "aria-label": "Load a .py file", onchange: async () => {
    const f = file.files[0];
    if (!f) return;
    if (f.size > MAX_BYTES) { banner.textContent = "That file is larger than the 50 KB limit."; return; }
    code.value = await f.text(); filename.value = f.name.replace(/[^A-Za-z0-9._-]/g, "_"); code.dispatchEvent(new Event("input"));
  } });

  const form = el("form", { class: "card", novalidate: true, onsubmit: async (ev) => {
    ev.preventDefault(); banner.textContent = "";
    if (!code.value.trim()) { banner.textContent = "Paste or load some Python code first."; return; }
    submit.disabled = true; submit.textContent = "Analyzing…";
    try {
      const body = { code: code.value, filename: filename.value.trim() || "snippet.py" };
      if (taskSel.value) body.task_id = Number(taskSel.value);
      const res = await Api.post("/analysis/python", body);
      window.location.href = "analysis-results.html?id=" + res.data.id;
    } catch (e) { banner.textContent = UI.errorText(e) + Object.values(e.details || {}).map((d) => " " + d).join(""); submit.disabled = false; submit.textContent = "Analyze code"; }
  } }, el("p", { class: "muted" }, "Your code is analysed as text only. It is never run on the server. Limit: 50 KB / 2,000 lines."), banner,
  el("div", { class: "grid cols-2" }, el("div", { class: "field" }, el("label", { for: "filename" }, "File name"), filename),
    el("div", { class: "field" }, el("label", { for: "task" }, "Link to task (optional)"), taskSel)),
  el("div", { class: "field" }, el("label", { for: "code" }, "Python source code"), code, counter),
  el("div", { class: "row" }, submit, el("label", { class: "btn", style: "margin:0" }, "Load .py file ", file)));

  async function loadHistory() {
    try {
      const res = await Api.get("/analysis/reports", { per_page: 10 });
      history.replaceChildren(UI.table([
        { label: "File", render: (r) => el("a", { href: "analysis-results.html?id=" + r.id }, r.filename) }, { label: "By", render: (r) => r.submitted_by_name },
        { label: "Lines", render: (r) => r.line_count }, { label: "Findings", render: (r) => `${r.summary.total} (${r.summary.critical + r.summary.high} high/critical)` },
        { label: "When", render: (r) => UI.fmtDateTime(r.created_at) }], res.data, "No analyses yet", "Submit code above to see results."));
    } catch (e) { history.replaceChildren(UI.errorBox(e)); }
  }
  main.append(Layout.pageHead("Code analysis", "Static analysis for Python: syntax errors, risky patterns, unused code and style problems."), form,
    el("div", { class: "card", style: "margin-top:1rem" }, el("h2", {}, "Recent analyses"), history));
  loadHistory();
  try { (await Api.get("/tasks", { per_page: 100, sort: "-created_at" })).data.filter((t) => t.status !== "Completed").forEach((t) => taskSel.append(el("option", { value: t.id }, t.title))); } catch (e) { /* optional */ }
})();
