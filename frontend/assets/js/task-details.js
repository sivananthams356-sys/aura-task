(async function () {
  const { el } = UI;
  const { user, main } = Layout.init({ page: "tasks" });
  const id = new URLSearchParams(location.search).get("id");
  if (!id) { window.location.href = "tasks.html"; return; }
  const holder = el("div", { class: "stack" }, UI.loading());
  main.append(holder);

  const METHOD = { ml_model: "Machine-learning estimate (model trained on synthetic demo data)", rule_based: "Rule-based estimate (not a trained ML prediction)" };

  async function load() {
    try {
      const t = (await Api.get("/tasks/" + id)).data;
      const [hist, comments, pred] = await Promise.all([
        Api.get(`/tasks/${id}/history`, { per_page: 50 }), Api.get(`/tasks/${id}/comments`),
        Api.get("/predictions/tasks/" + id).catch(() => null)]);
      render(t, hist.data, comments.data, pred && pred.data);
    } catch (e) { holder.replaceChildren(UI.errorBox(e)); }
  }

  const run = (fn, msg) => async () => { if (await UI.act(fn, msg)) load(); };
  const post = (path, body) => () => Api.post(`/tasks/${id}/${path}`, body);

  function actions(t) {
    const isAssignee = t.assignee_id === user.id;
    const isMgr = user.role === "manager" && t.manager_id === user.id;
    const isAdmin = user.role === "admin";
    const b = [];
    const btn = (label, fn, cls) => b.push(el("button", { class: "btn sm " + (cls || ""), onclick: fn }, label));
    if (t.status === "Pending" && (isAssignee || isMgr || isAdmin)) btn("Start task", run(post("status", { status: "In Progress" }), "Task started"), "primary");
    if (t.status === "In Progress" && isAssignee) {
      btn("Update progress", () => UI.openForm({ title: "Update progress", fields: [
        { name: "progress", label: "Progress (0–99%)", type: "number", min: 0, max: 99, required: true, value: t.progress },
        { name: "actual_hours", label: "Total hours worked so far", type: "number", step: "0.5", min: 0, value: t.actual_hours },
        { name: "note", label: "Progress note", type: "textarea", rows: 3 }],
        onSubmit: async (v) => { await Api.post(`/tasks/${id}/progress`, v); UI.toast("Progress updated", "success"); load(); } }), "primary");
      b.push(el("button", { class: "btn sm", disabled: t.progress < 90, title: t.progress < 90 ? "Reach at least 90% first" : "", onclick: () => UI.openForm({
        title: "Submit for review", fields: [{ name: "note", label: "Note for your manager", type: "textarea", rows: 3 }], submitText: "Submit",
        onSubmit: async (v) => { await Api.post(`/tasks/${id}/submit`, v); UI.toast("Submitted for review", "success"); load(); } }) }, "Submit for review"));
    }
    if (t.status === "In Progress" && (isAssignee || isMgr)) btn("Mark blocked", () => UI.openForm({ title: "Mark as blocked",
      fields: [{ name: "reason", label: "Reason", type: "textarea", required: true, rows: 3 }], onSubmit: async (v) => {
        await Api.post(`/tasks/${id}/status`, { status: "Blocked", reason: v.reason }); UI.toast("Task blocked", "success"); load(); } }));
    if (t.status === "Blocked" && (isAssignee || isMgr)) btn("Resume", run(post("status", { status: "In Progress" }), "Task resumed"), "primary");
    if (t.status === "Under Review" && isMgr) {
      btn("Approve", () => UI.openForm({ title: "Approve task", submitText: "Approve", fields: [{ name: "feedback", label: "Feedback (optional)", type: "textarea", rows: 3 }],
        onSubmit: async (v) => { await Api.post(`/tasks/${id}/review`, { decision: "approve", feedback: v.feedback }); UI.toast("Task approved", "success"); load(); } }), "primary");
      btn("Reject", () => UI.openForm({ title: "Reject task", submitText: "Reject", fields: [{ name: "feedback", label: "What needs to change?", type: "textarea", required: true, rows: 3 }],
        onSubmit: async (v) => { await Api.post(`/tasks/${id}/review`, { decision: "reject", feedback: v.feedback }); UI.toast("Task sent back", "success"); load(); } }), "danger");
    }
    if (t.status === "Completed" && (isMgr || isAdmin)) btn("Reopen", () => UI.openForm({ title: "Reopen task",
      fields: [{ name: "reason", label: "Reason", type: "textarea", required: true, rows: 3 }], onSubmit: async (v) => {
        await Api.post(`/tasks/${id}/reopen`, v); UI.toast("Task reopened", "success"); load(); } }));
    if ((isMgr || isAdmin) && t.status !== "Completed") b.push(el("a", { class: "btn sm", href: "task-form.html?id=" + id }, "Edit"));
    if (isMgr || isAdmin) btn("Archive", async () => {
      if (await UI.confirmDialog("Archive this task? It will disappear from lists.", "Archive") && await UI.act(post("archive"), "Task archived")) window.location.href = "tasks.html"; });
    return el("div", { class: "row" }, b);
  }

  function predictionCard(p) {
    if (!p) return null;
    return el("div", { class: "card" }, el("h2", {}, "Delay-risk estimate ", UI.badge(p.risk_category)),
      el("p", { class: "small muted" }, METHOD[p.method], p.risk_score !== null ? ` · model score ${p.risk_score}` : "", " · ", UI.fmtDateTime(p.predicted_at)),
      p.factors.length ? el("ul", { class: "list-plain" }, p.factors.map((f) => el("li", {}, f.reason, el("span", { class: "muted small" }, f.effect === "increases_risk" ? " (raises risk)" : " (lowers risk)")))) : el("p", { class: "muted" }, "No single factor stands out."),
      el("h3", { style: "margin-top:.75rem" }, "Suggested actions"), el("ul", {}, p.suggested_actions.map((a) => el("li", {}, a))),
      el("p", { class: "muted small" }, p.disclaimer));
  }

  function render(t, hist, comments, pred) {
    const box = el("textarea", { rows: 3, "aria-label": "Add a comment", placeholder: "Write a comment…" });
    holder.replaceChildren(
      Layout.pageHead(t.title, null, el("a", { class: "btn sm", href: "tasks.html" }, "← Back to tasks")),
      el("div", { class: "card" }, el("div", { class: "row", style: "margin-bottom:.75rem" }, UI.badge(t.status), UI.badge(t.priority),
        t.is_overdue ? el("span", { class: "overdue" }, "Overdue") : null, t.is_archived ? UI.badge("Archived") : null),
        el("p", {}, t.description || el("span", { class: "muted" }, "No description.")), UI.progressBar(t.progress),
        el("p", { class: "muted small" }, t.progress + "% complete"),
        el("dl", { class: "kv" },
          el("dt", {}, "Project"), el("dd", {}, t.project_name), el("dt", {}, "Assignee"), el("dd", {}, t.assignee_name),
          el("dt", {}, "Manager"), el("dd", {}, t.manager_name), el("dt", {}, "Start date"), el("dd", {}, UI.fmtDate(t.start_date)),
          el("dt", {}, "Deadline"), el("dd", {}, UI.fmtDate(t.deadline)), el("dt", {}, "Estimated effort"), el("dd", {}, t.estimated_hours ? t.estimated_hours + " h" : "—"),
          el("dt", {}, "Actual effort"), el("dd", {}, t.actual_hours != null ? t.actual_hours + " h" : "—"),
          el("dt", {}, "Review rejections"), el("dd", {}, t.rejection_count), el("dt", {}, "Reopenings"), el("dd", {}, t.reopen_count),
          el("dt", {}, "Last progress update"), el("dd", {}, UI.fmtDateTime(t.last_progress_update)),
          el("dt", {}, "Review feedback"), el("dd", {}, t.review_feedback || "—"), el("dt", {}, "Completed"), el("dd", {}, UI.fmtDateTime(t.completed_at))),
        el("div", { style: "margin-top:1rem" }, actions(t))),
      predictionCard(pred),
      el("div", { class: "grid cols-2" },
        el("div", { class: "card" }, el("h2", {}, "Comments"),
          comments.length ? el("ul", { class: "list-plain" }, comments.map((c) => el("li", {}, el("strong", {}, c.author_name), " ", el("span", { class: "muted small" }, UI.fmtDateTime(c.created_at)), el("div", {}, c.body)))) : UI.empty("No comments yet"),
          el("div", { class: "field" }, box),
          el("button", { class: "btn primary sm", onclick: async () => {
            if (!box.value.trim()) return;
            if (await UI.act(() => Api.post(`/tasks/${id}/comments`, { body: box.value.trim() }), "Comment added")) load(); } }, "Add comment")),
        el("div", { class: "card" }, el("h2", {}, "History"),
          UI.table([{ label: "When", render: (h) => UI.fmtDateTime(h.created_at) }, { label: "Who", render: (h) => h.actor_name },
            { label: "What", render: (h) => h.action.replace(/_/g, " ") + (h.field ? ` (${h.field}: ${h.old_value ?? "—"} → ${h.new_value ?? "—"})` : "") }], hist, "No history"))));
  }
  load();
})();
