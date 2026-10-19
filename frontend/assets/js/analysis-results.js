(async function () {
  const { el } = UI;
  const { main } = Layout.init({ page: "code" });
  const id = new URLSearchParams(location.search).get("id");
  if (!id) { window.location.href = "code-analysis.html"; return; }
  const holder = el("div", { class: "stack" }, UI.loading());
  main.append(holder);
  try {
    const r = (await Api.get("/analysis/reports/" + id)).data;
    let active = "all";
    const list = el("div"), chips = el("div", { class: "chips", role: "group", "aria-label": "Filter by severity" });
    const lines = r.code.split("\n");
    const flagged = new Set(r.findings.map((f) => f.line).filter(Boolean));
    const codeView = el("div", { class: "codeview", tabindex: "0", "aria-label": "Submitted source code" }, lines.map((text, i) =>
      el("div", { class: "ln" + (flagged.has(i + 1) ? " flag" : ""), id: "L" + (i + 1) }, el("span", { class: "no" }, i + 1), el("span", { class: "tx" }, text || " "))));

    function draw() {
      const shown = r.findings.filter((f) => active === "all" || f.severity === active);
      list.replaceChildren(UI.table([
        { label: "Line", render: (f) => f.line ? el("a", { href: "#L" + f.line }, f.line) : "—" }, { label: "Severity", render: (f) => UI.badge(f.severity) },
        { label: "Finding", render: (f) => el("div", {}, el("strong", {}, f.message), el("div", { class: "muted small" }, `${f.rule_id} · ${f.category.replace(/_/g, " ")} · ${f.tool}`)) },
        { label: "Why it matters", render: (f) => f.explanation }, { label: "Suggested fix", render: (f) => f.suggestion }],
      shown, r.findings.length ? "No findings for this filter" : "No issues found", r.findings.length ? "" : "The checks that ran found nothing. This does not prove the code is bug-free."));
      chips.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.sev === active)));
    }
    [["all", `All (${r.summary.total})`], ...["critical", "high", "medium", "low", "info"].map((s) => [s, `${s} (${r.summary[s]})`])].forEach(([sev, label]) =>
      chips.append(el("button", { class: "chip", "data-sev": sev, onclick: () => { active = sev; draw(); } }, label)));

    holder.replaceChildren(
      Layout.pageHead(r.filename, `Analysed ${UI.fmtDateTime(r.created_at)} by ${r.submitted_by_name} · ${r.line_count} lines`, el("a", { class: "btn sm", href: "code-analysis.html" }, "← New analysis")),
      el("div", { class: "alert" }, r.disclaimer, " Tools used: ", r.tools_used.join(", "), ".", r.notes.map((n) => el("div", {}, n))),
      r.syntax_valid ? null : el("div", { class: "alert error" }, "This code has a syntax error, so deeper checks were skipped."),
      el("div", { class: "card" }, el("h2", {}, "Findings"), chips, el("div", { style: "margin-top:.75rem" }, list)),
      el("div", { class: "card" }, el("h2", {}, "Source code"), el("p", { class: "muted small" }, "Highlighted lines have at least one finding."), codeView));
    draw();
  } catch (e) { holder.replaceChildren(UI.errorBox(e)); }
})();
