(async function () {
  const { el } = UI;
  const { user, main } = Layout.init({ page: "tasks" });
  const canCreate = user.role !== "employee";
  const state = { page: 1, q: "", status: "", priority: "", overdue: "", sort: "deadline" };
  const results = el("div");

  async function load() {
    results.replaceChildren(UI.loading());
    try {
      const res = await Api.get("/tasks", { page: state.page, per_page: 12, q: state.q, status: state.status, priority: state.priority, overdue: state.overdue, sort: state.sort });
      const cols = [{ label: "Task", render: (t) => el("a", { href: "task-details.html?id=" + t.id }, t.title) },
        { label: "Project", render: (t) => t.project_name }];
      if (user.role !== "employee") cols.push({ label: "Assignee", render: (t) => t.assignee_name });
      cols.push({ label: "Priority", render: (t) => UI.badge(t.priority) }, { label: "Status", render: (t) => UI.badge(t.status) },
        { label: "Progress", render: (t) => el("div", { style: "min-width:90px" }, UI.progressBar(t.progress), el("span", { class: "muted small" }, t.progress + "%")) },
        { label: "Deadline", render: (t) => el("span", { class: t.is_overdue ? "overdue" : "" }, UI.fmtDate(t.deadline), t.is_overdue ? " (overdue)" : "") });
      results.replaceChildren(UI.table(cols, res.data, "No tasks found", canCreate ? "Create a task or change the filters." : "Tasks assigned to you will appear here."),
        UI.pager(res.meta, (p) => { state.page = p; load(); }));
    } catch (e) { results.replaceChildren(UI.errorBox(e)); }
  }

  const sel = (label, key, options) => {
    const s = el("select", { "aria-label": label }, options.map(([v, l]) => el("option", { value: v }, l)));
    s.addEventListener("change", () => { state[key] = s.value; state.page = 1; load(); });
    return s;
  };
  const search = el("input", { type: "search", placeholder: "Search by title", "aria-label": "Search tasks" });
  let timer;
  search.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => { state.q = search.value.trim(); state.page = 1; load(); }, 300); });

  main.append(Layout.pageHead(user.role === "employee" ? "My tasks" : "Tasks", null,
    canCreate ? el("a", { class: "btn primary", href: "task-form.html" }, "New task") : null),
    el("div", { class: "filters" }, search,
      sel("Status", "status", [["", "Any status"], ...["Pending", "In Progress", "Under Review", "Completed", "Blocked"].map((s) => [s, s])]),
      sel("Priority", "priority", [["", "Any priority"], ...["Low", "Medium", "High", "Critical"].map((s) => [s, s])]),
      sel("Overdue", "overdue", [["", "All deadlines"], ["true", "Overdue only"]]),
      sel("Sort", "sort", [["deadline", "Deadline (soonest)"], ["-deadline", "Deadline (latest)"], ["-priority", "Priority (high first)"], ["-progress", "Progress (high first)"], ["-created_at", "Newest"]])),
    results);
  load();
})();
