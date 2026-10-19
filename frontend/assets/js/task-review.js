(async function () {
  const { el } = UI;
  const { main } = Layout.init({ page: "review", roles: ["manager"] });
  const results = el("div", { class: "stack" });
  main.append(Layout.pageHead("Task reviews", "Tasks your team has submitted for approval."), results);

  async function load() {
    results.replaceChildren(UI.loading());
    try {
      const res = await Api.get("/tasks", { status: "Under Review", per_page: 50, sort: "deadline" });
      if (!res.data.length) { results.replaceChildren(UI.empty("Nothing waiting for review", "Submitted tasks appear here.")); return; }
      results.replaceChildren(...res.data.map((t) => el("div", { class: "card" },
        el("div", { class: "row", style: "justify-content:space-between" }, el("h2", {}, el("a", { href: "task-details.html?id=" + t.id }, t.title)), UI.badge(t.priority)),
        el("p", { class: "muted small" }, `${t.assignee_name} · ${t.project_name} · deadline ${UI.fmtDate(t.deadline)}${t.rejection_count ? ` · rejected ${t.rejection_count}×` : ""}`),
        UI.progressBar(t.progress),
        el("div", { class: "row", style: "margin-top:.75rem" },
          el("button", { class: "btn primary sm", onclick: () => UI.openForm({ title: "Approve: " + t.title, submitText: "Approve", fields: [{ name: "feedback", label: "Feedback (optional)", type: "textarea", rows: 3 }],
            onSubmit: async (v) => { await Api.post(`/tasks/${t.id}/review`, { decision: "approve", feedback: v.feedback }); UI.toast("Task approved", "success"); load(); } }) }, "Approve"),
          el("button", { class: "btn danger sm", onclick: () => UI.openForm({ title: "Reject: " + t.title, submitText: "Reject", fields: [{ name: "feedback", label: "What needs to change?", type: "textarea", required: true, rows: 3 }],
            onSubmit: async (v) => { await Api.post(`/tasks/${t.id}/review`, { decision: "reject", feedback: v.feedback }); UI.toast("Task sent back", "success"); load(); } }) }, "Reject")))));
    } catch (e) { results.replaceChildren(UI.errorBox(e)); }
  }
  load();
})();
