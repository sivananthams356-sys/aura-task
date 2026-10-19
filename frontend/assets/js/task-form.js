(async function () {
  const { el } = UI;
  const { main } = Layout.init({ page: "tasks", roles: ["admin", "manager"] });
  const id = new URLSearchParams(location.search).get("id");
  main.append(Layout.pageHead(id ? "Edit task" : "New task"), UI.loading());
  try {
    const [projects, employees, existing] = await Promise.all([
      Api.get("/projects", { per_page: 100 }), Api.get("/users", { role: "employee", is_active: "true", per_page: 100 }),
      id ? Api.get("/tasks/" + id) : Promise.resolve(null)]);
    const t = existing && existing.data;
    if (!projects.data.length) { main.lastChild.replaceWith(UI.empty("No projects available", "Ask an administrator to add you to a project first.")); return; }
    if (!employees.data.length) { main.lastChild.replaceWith(UI.empty("No employees available", "You need active team members to assign tasks.")); return; }
    const today = new Date().toISOString().slice(0, 10);
    const f = UI.buildFields([
      { name: "title", label: "Title", required: true, value: t && t.title },
      { name: "description", label: "Description", type: "textarea", value: t && t.description },
      { name: "project_id", label: "Project", type: "select", numeric: true, required: true, disabled: !!t, value: t && t.project_id,
        options: projects.data.map((p) => ({ value: p.id, label: p.name })) },
      { name: "assignee_id", label: "Assign to", type: "select", numeric: true, required: true, value: t && t.assignee_id,
        options: employees.data.map((u) => ({ value: u.id, label: u.name })) },
      { name: "priority", label: "Priority", type: "select", required: true, value: t ? t.priority : "Medium",
        options: ["Low", "Medium", "High", "Critical"].map((p) => ({ value: p, label: p })) },
      { name: "start_date", label: "Start date", type: "date", value: t ? t.start_date : today },
      { name: "deadline", label: "Deadline", type: "date", required: true, value: t && t.deadline },
      { name: "estimated_hours", label: "Estimated effort (hours)", type: "number", step: "0.5", min: "0.5", required: true, value: t && t.estimated_hours }]);
    const submit = el("button", { class: "btn primary", type: "submit" }, id ? "Save changes" : "Create task");
    const form = el("form", { class: "card", novalidate: true, style: "max-width:640px", onsubmit: async (ev) => {
      ev.preventDefault();
      const v = f.check();
      if (!v) return;
      if (t) delete v.project_id;
      submit.disabled = true;
      try {
        const res = id ? await Api.patch("/tasks/" + id, v) : await Api.post("/tasks", v);
        window.location.href = "task-details.html?id=" + res.data.id;
      } catch (e) { f.showError(e); submit.disabled = false; }
    } }, f.banner, f.nodes, el("div", { class: "row" }, submit, el("a", { class: "btn", href: id ? "task-details.html?id=" + id : "tasks.html" }, "Cancel")));
    main.lastChild.replaceWith(form);
  } catch (e) { main.lastChild.replaceWith(UI.errorBox(e)); }
})();
