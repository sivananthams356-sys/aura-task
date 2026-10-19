(async function () {
  const { el } = UI;
  const { user, main } = Layout.init({ page: "reports" });
  const out = el("div", { class: "stack" });
  const iso = (d) => d.toISOString().slice(0, 10);
  const from = el("input", { type: "date", "aria-label": "From", value: iso(new Date(Date.now() - 30 * 864e5)) });
  const to = el("input", { type: "date", "aria-label": "To", value: iso(new Date()) });
  const canExport = user.role !== "employee";

  async function load() {
    out.replaceChildren(UI.loading());
    try {
      const d = (await Api.get("/reports/summary", { from: from.value, to: to.value })).data, t = d.totals;
      const stat = (n, l) => el("div", { class: "card stat" }, el("div", { class: "num" }, n), el("div", { class: "lbl" }, l));
      const r = d.risk_distribution, a = d.analysis_by_severity;
      out.replaceChildren(
        el("div", { class: "grid cols-4" }, stat(t.total, "Total tasks"), stat(t.pending, "Pending"), stat(t.in_progress, "In progress"), stat(t.completed, "Completed"), stat(t.overdue, "Overdue")),
        el("div", { class: "grid cols-2" },
          el("div", { class: "card" }, el("h2", {}, "Tasks by priority"), UI.bars(["Low", "Medium", "High", "Critical"].map((p) => ({ label: p, value: d.by_priority[p] })))),
          el("div", { class: "card" }, el("h2", {}, "Delay-risk distribution"), UI.bars([{ label: "Low", value: r.Low }, { label: "Medium", value: r.Medium }, { label: "High", value: r.High }, { label: "Not scored", value: r.unscored, tone: "unscored" }]),
            el("p", { class: "muted small" }, "From stored predictions (ML trained on synthetic demo data, or rule-based). Not proof of real-world accuracy."))),
        el("div", { class: "grid cols-2" },
          el("div", { class: "card" }, el("h2", {}, `Completions (${d.range.from} to ${d.range.to})`),
            d.completion_trend.length ? UI.bars(d.completion_trend.map((x) => ({ label: UI.fmtDate(x.date), value: x.completed, tone: "Low" }))) : UI.empty("No completions in this range")),
          el("div", { class: "card" }, el("h2", {}, "Review rejections and reopenings"),
            UI.table([{ label: "Date", render: (x) => UI.fmtDate(x.date) }, { label: "Rejections", render: (x) => x.rejections }, { label: "Reopenings", render: (x) => x.reopenings }], d.rejection_trend, "None in this range"))),
        el("div", { class: "card" }, el("h2", {}, "Code-analysis findings by severity"),
          UI.bars(["critical", "high", "medium", "low", "info"].map((s) => ({ label: s, value: a[s], tone: s })))),
        d.by_employee ? el("div", { class: "card" }, el("h2", {}, "Tasks by employee"),
          UI.table([{ label: "Employee", render: (x) => x.name }, { label: "Total", render: (x) => x.total }, { label: "Completed", render: (x) => x.completed }, { label: "Overdue", render: (x) => x.overdue }], d.by_employee, "No data")) : null);
    } catch (e) { out.replaceChildren(UI.errorBox(e)); }
  }
  const dl = (path, name) => () => UI.act(() => Api.download(path, name));
  main.append(Layout.pageHead("Reports and analytics", "All figures come from your authorised data.",
    canExport ? el("button", { class: "btn", onclick: dl("/reports/export/tasks.csv", "tasks.csv") }, "Export tasks (CSV)") : null,
    canExport ? el("button", { class: "btn", onclick: dl("/reports/export/analysis.csv", "analysis.csv") }, "Export analysis (CSV)") : null),
  el("div", { class: "filters" }, el("label", { class: "sr-only" }, "From"), from, el("label", { class: "sr-only" }, "To"), to,
    el("button", { class: "btn primary", onclick: load }, "Apply range")), out);
  load();
})();
