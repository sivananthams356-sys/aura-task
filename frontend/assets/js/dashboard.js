(async function () {
  const { el } = UI;
  const role = document.body.dataset.role;
  const { user, main } = Layout.init({ page: "dashboard", roles: [role] });
  main.append(Layout.pageHead(`Welcome, ${user.name}`, {
    admin: "Organisation-wide overview", manager: "Overview of your team", employee: "Your tasks at a glance" }[role]),
    UI.loading());
  const body = el("div", { class: "stack" });
  try {
    const [stats, tasks, risky] = await Promise.all([
      Api.get("/dashboard/stats"),
      Api.get("/tasks", { per_page: 6, sort: "deadline", status: role === "employee" ? "In Progress" : undefined }),
      role === "manager" ? Api.get("/predictions", { risk_category: "High", per_page: 5 }) : Promise.resolve(null),
    ]);
    const s = stats.data, t = s.tasks;
    const stat = (n, label, warn) => el("div", { class: "card stat" + (warn && n ? " warn" : "") }, el("div", { class: "num" }, n), el("div", { class: "lbl" }, label));
    const tiles = [stat(t.total, "Total tasks"), stat(t.pending, "Pending"), stat(t.in_progress, "In progress"),
      stat(t.under_review, "Under review"), stat(t.completed, "Completed"), stat(t.blocked, "Blocked", true), stat(t.overdue, "Overdue", true)];
    if (role === "manager") tiles.push(stat(s.pending_reviews, "Waiting for your review", true));
    if (role === "admin") tiles.push(stat(`${s.users.active}/${s.users.total}`, "Active users"));
    const r = s.risk_distribution;
    body.append(el("div", { class: "grid cols-4" }, tiles),
      el("div", { class: "grid cols-2" },
        el("div", { class: "card" }, el("h2", {}, "Tasks by priority"),
          UI.bars(["Low", "Medium", "High", "Critical"].map((p) => ({ label: p, value: s.by_priority[p] })))),
        el("div", { class: "card" }, el("h2", {}, "Delay-risk distribution"),
          UI.bars([{ label: "Low", value: r.Low }, { label: "Medium", value: r.Medium }, { label: "High", value: r.High },
            { label: "Not scored", value: r.unscored, tone: "unscored" }]),
          el("p", { class: "muted small" }, "Based on the latest stored predictions. ",
            role !== "employee" ? el("a", { href: "risk-dashboard.html" }, "Open the delay-risk dashboard") : ""))),
      el("div", { class: "grid cols-2" },
        el("div", { class: "card" }, el("h2", {}, role === "employee" ? "Your active tasks" : "Soonest deadlines"),
          UI.table([{ label: "Task", render: (x) => el("a", { href: "task-details.html?id=" + x.id }, x.title) },
            { label: "Status", render: (x) => UI.badge(x.status) }, { label: "Deadline", render: (x) => UI.fmtDate(x.deadline) }],
          tasks.data, "No tasks to show", role === "employee" ? "Tasks assigned to you will appear here." : "")),
        role === "manager" ? el("div", { class: "card" }, el("h2", {}, "Highest-risk tasks"),
          UI.table([{ label: "Task", render: (x) => el("a", { href: "task-details.html?id=" + x.task_id }, x.title) },
            { label: "Assignee", render: (x) => x.assignee_name }, { label: "Risk", render: (x) => UI.badge(x.risk_category) }],
          risky.data, "No high-risk tasks", "Run predictions on the Delay Risk page to score your open tasks.")) :
        el("div", { class: "card" }, el("h2", {}, "Upcoming deadlines"),
          UI.table([{ label: "Task", render: (x) => el("a", { href: "task-details.html?id=" + x.task_id }, x.title) },
            { label: "Deadline", render: (x) => UI.fmtDate(x.deadline) }], s.upcoming_deadlines, "No upcoming deadlines"))));
    main.lastChild.replaceWith(body);
  } catch (e) { main.lastChild.replaceWith(UI.errorBox(e)); }
})();
