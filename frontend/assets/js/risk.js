(async function () {
  const { el } = UI;
  const { main } = Layout.init({ page: "risk", roles: ["admin", "manager"] });
  const info = el("div"), results = el("div");
  let category = "";

  async function loadInfo() {
    try {
      const m = (await Api.get("/predictions/model-info")).data;
      info.replaceChildren(el("div", { class: "alert" }, el("strong", {}, m.model_available ? "Trained model in use. " : "No trained model: rule-based estimates only. "),
        m.model_available ? `Version ${m.model_version}, trained on ${m.trained_on} data. Test metrics (synthetic data, NOT real-world accuracy): precision ${m.metrics.precision}, recall ${m.metrics.recall}, F1 ${m.metrics.f1}, ROC-AUC ${m.metrics.roc_auc}; baseline F1 ${m.metrics.baseline_f1}.` : m.notes));
    } catch (e) { info.replaceChildren(UI.errorBox(e)); }
  }

  async function load() {
    results.replaceChildren(UI.loading());
    try {
      const res = await Api.get("/predictions", { risk_category: category, per_page: 50 });
      results.replaceChildren(UI.table([
        { label: "Task", render: (p) => el("a", { href: "task-details.html?id=" + p.task_id }, p.title) }, { label: "Assignee", render: (p) => p.assignee_name },
        { label: "Deadline", render: (p) => UI.fmtDate(p.deadline) }, { label: "Risk", render: (p) => UI.badge(p.risk_category) },
        { label: "Score", render: (p) => p.risk_score === null ? "n/a (rule-based)" : p.risk_score },
        { label: "Main reason", render: (p) => p.factors.length ? p.factors[0].reason : "—" }, { label: "Suggested action", render: (p) => p.suggested_actions[0] }],
      res.data, "No predictions yet", "Click “Score all open tasks” to generate them."), UI.pager(res.meta, () => {}));
    } catch (e) { results.replaceChildren(UI.errorBox(e)); }
  }

  const filter = el("select", { "aria-label": "Filter by risk" }, el("option", { value: "" }, "All risk levels"), ["High", "Medium", "Low"].map((c) => el("option", { value: c }, c)));
  filter.addEventListener("change", () => { category = filter.value; load(); });
  const runBtn = el("button", { class: "btn primary", onclick: async () => {
    runBtn.disabled = true; runBtn.textContent = "Scoring…";
    if (await UI.act(async () => { const r = await Api.post("/predictions/run", {}); UI.toast(`${r.data.scored} task(s) scored`, "success"); })) { load(); loadInfo(); }
    runBtn.disabled = false; runBtn.textContent = "Score all open tasks";
  } }, "Score all open tasks");
  main.append(Layout.pageHead("Task delay risk", "Estimates which open tasks may miss their deadline.", runBtn), info, el("div", { class: "filters" }, filter), results);
  loadInfo(); load();
})();
