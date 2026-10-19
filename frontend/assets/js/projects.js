(async function () {
  const { el } = UI;
  const { main } = Layout.init({ page: "projects", roles: ["admin"] });
  const results = el("div");
  let showArchived = false, people = [];

  const fields = (p) => [
    { name: "name", label: "Project name", required: true, value: p && p.name },
    { name: "description", label: "Description", type: "textarea", value: p && p.description },
    { name: "member_ids", label: "Members", type: "multiselect", value: p ? p.member_ids : [],
      options: people.map((u) => ({ value: u.id, label: `${u.name} (${u.role})` })) }];

  async function load() {
    results.replaceChildren(UI.loading());
    try {
      const res = await Api.get("/projects", { is_archived: showArchived ? "true" : "false", per_page: 100 });
      results.replaceChildren(UI.table([
        { label: "Project", render: (p) => el("strong", {}, p.name) }, { label: "Description", render: (p) => p.description || "—" },
        { label: "Members", render: (p) => p.member_ids.length }, { label: "Created", render: (p) => UI.fmtDate(p.created_at) },
        { label: "Actions", render: (p) => p.is_archived ? UI.badge("Archived") : el("div", { class: "row" },
          el("button", { class: "btn sm", onclick: () => UI.openForm({ title: "Edit project", fields: fields(p), onSubmit: async (v) => {
            await Api.patch("/projects/" + p.id, { name: v.name, description: v.description || "", member_ids: v.member_ids || [] }); UI.toast("Project updated", "success"); load(); } }) }, "Edit"),
          el("button", { class: "btn sm", onclick: async () => {
            if (await UI.confirmDialog(`Archive "${p.name}"? No new tasks can be created in it.`, "Archive") && await UI.act(() => Api.post(`/projects/${p.id}/archive`), "Project archived")) load(); } }, "Archive")) }],
      res.data, "No projects yet", "Create a project and add its members."));
    } catch (e) { results.replaceChildren(UI.errorBox(e)); }
  }

  const toggle = el("input", { type: "checkbox", id: "arch", style: "width:auto", onchange: (ev) => { showArchived = ev.target.checked; load(); } });
  main.append(Layout.pageHead("Projects", "Group tasks and decide who works on what.",
    el("button", { class: "btn primary", onclick: () => UI.openForm({ title: "New project", submitText: "Create", fields: fields(null), onSubmit: async (v) => {
      await Api.post("/projects", { name: v.name, description: v.description, member_ids: v.member_ids || [] }); UI.toast("Project created", "success"); load(); } }) }, "New project")),
    el("div", { class: "filters" }, el("label", { class: "check", for: "arch" }, toggle, "Show archived")), results);
  try { people = (await Api.get("/users", { is_active: "true", per_page: 100 })).data.filter((u) => u.role !== "admin"); } catch (e) { UI.toast(UI.errorText(e), "error"); }
  load();
})();
