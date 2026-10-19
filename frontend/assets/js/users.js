(async function () {
  const { el } = UI;
  const { user, main } = Layout.init({ page: "users", roles: ["admin", "manager"] });
  const isAdmin = user.role === "admin";
  const state = { page: 1, q: "", role: "", active: "" };
  let managers = [];
  const results = el("div");

  const roleOptions = [{ value: "employee", label: "Employee" }, { value: "manager", label: "Manager" }, { value: "admin", label: "Admin" }];
  const managerOptions = () => managers.map((m) => ({ value: m.id, label: m.name }));

  function userFields(existing) {
    const f = [
      { name: "name", label: "Full name", required: true, value: existing && existing.name },
      { name: "role", label: "Role", type: "select", options: roleOptions, value: existing && existing.role },
      { name: "manager_id", label: "Manager (required for employees)", type: "select", numeric: true,
        options: [{ value: "", label: "— none —" }, ...managerOptions()], value: existing && existing.manager_id },
    ];
    if (!existing) f.splice(1, 0,
      { name: "email", label: "Email", type: "email", required: true },
      { name: "password", label: "Temporary password", type: "password", required: true, hint: "At least 10 characters with a letter and a number." });
    return f;
  }

  async function load() {
    results.replaceChildren(UI.loading());
    try {
      const res = await Api.get("/users", { page: state.page, per_page: 15, q: state.q, role: state.role, is_active: state.active });
      const names = Object.fromEntries(managers.map((m) => [m.id, m.name]));
      const cols = [
        { label: "Name", render: (u) => u.name }, { label: "Email", render: (u) => u.email },
        { label: "Role", render: (u) => UI.badge(u.role) },
        { label: "Manager", render: (u) => names[u.manager_id] || "—" },
        { label: "Status", render: (u) => UI.badge(u.is_active ? "Active" : "Inactive") }];
      if (isAdmin) cols.push({ label: "Actions", render: (u) => el("div", { class: "row" },
        el("button", { class: "btn sm", onclick: () => UI.openForm({ title: "Edit user", fields: userFields(u), onSubmit: async (v) => {
          await Api.patch("/users/" + u.id, { name: v.name, role: v.role, manager_id: v.manager_id }); UI.toast("User updated", "success"); load(); } }) }, "Edit"),
        el("button", { class: "btn sm", onclick: async () => {
          if (u.is_active && !(await UI.confirmDialog(`Deactivate ${u.name}? They will no longer be able to log in.`, "Deactivate"))) return;
          if (await UI.act(() => Api.post(`/users/${u.id}/${u.is_active ? "deactivate" : "activate"}`), "Account updated")) load(); } }, u.is_active ? "Deactivate" : "Activate"),
        el("button", { class: "btn sm", onclick: () => UI.openForm({ title: "Reset password for " + u.name,
          fields: [{ name: "new_password", label: "New password", type: "password", required: true }],
          onSubmit: async (v) => { await Api.post(`/users/${u.id}/reset-password`, v); UI.toast("Password reset", "success"); } }) }, "Reset password")) });
      results.replaceChildren(UI.table(cols, res.data, "No users found", "Try different filters."), UI.pager(res.meta, (p) => { state.page = p; load(); }));
    } catch (e) { results.replaceChildren(UI.errorBox(e)); }
  }

  const search = el("input", { type: "search", placeholder: "Search name or email", "aria-label": "Search users" });
  const roleSel = el("select", { "aria-label": "Filter by role" }, el("option", { value: "" }, "All roles"), roleOptions.map((o) => el("option", { value: o.value }, o.label)));
  const activeSel = el("select", { "aria-label": "Filter by status" }, el("option", { value: "" }, "Any status"), el("option", { value: "true" }, "Active"), el("option", { value: "false" }, "Inactive"));
  let timer;
  search.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => { state.q = search.value.trim(); state.page = 1; load(); }, 300); });
  roleSel.addEventListener("change", () => { state.role = roleSel.value; state.page = 1; load(); });
  activeSel.addEventListener("change", () => { state.active = activeSel.value; state.page = 1; load(); });

  main.append(Layout.pageHead(isAdmin ? "User management" : "My team", isAdmin ? "Create and manage employee, manager and admin accounts." : "Employees assigned to you.",
    isAdmin ? el("button", { class: "btn primary", onclick: () => UI.openForm({ title: "Create user", submitText: "Create", fields: userFields(null), onSubmit: async (v) => {
      await Api.post("/users", v); UI.toast("User created", "success"); load(); } }) }, "New user") : null),
    el("div", { class: "filters" }, search, isAdmin ? roleSel : null, activeSel), results);
  try { managers = (await Api.get("/users", { role: "manager", per_page: 100 })).data; if (!isAdmin) managers = [user]; } catch (e) { managers = isAdmin ? [] : [user]; }
  load();
})();
