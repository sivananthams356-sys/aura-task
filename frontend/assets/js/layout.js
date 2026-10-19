/* Page shell: sidebar navigation (per role), session check, logout. */
const Layout = (() => {
  const { el } = UI;
  const DASH = { admin: "admin-dashboard.html", manager: "manager-dashboard.html", employee: "employee-dashboard.html" };
  const ALL = ["admin", "manager", "employee"];
  const NAV = [
    { key: "dashboard", label: () => "Dashboard", href: (r) => DASH[r], roles: ALL },
    { key: "users", label: (r) => (r === "manager" ? "My Team" : "Users"), href: () => "users.html", roles: ["admin", "manager"] },
    { key: "projects", label: () => "Projects", href: () => "projects.html", roles: ["admin"] },
    { key: "tasks", label: (r) => (r === "employee" ? "My Tasks" : "Tasks"), href: () => "tasks.html", roles: ALL },
    { key: "review", label: () => "Task Reviews", href: () => "task-review.html", roles: ["manager"] },
    { key: "risk", label: () => "Delay Risk (AI)", href: () => "risk-dashboard.html", roles: ["admin", "manager"] },
    { key: "code", label: () => "Code Analysis", href: () => "code-analysis.html", roles: ALL },
    { key: "reports", label: () => "Reports", href: () => "reports.html", roles: ALL },
    { key: "profile", label: () => "Profile", href: () => "profile.html", roles: ALL },
  ];

  async function logout() {
    try { await Api.post("/auth/logout"); } catch (e) { /* token may already be invalid */ }
    Api.clearSession();
    window.location.href = "login.html";
  }

  function init({ page, roles }) {
    const user = Api.user();
    if (!Api.token() || !user) { window.location.href = "login.html"; throw new Error("redirect"); }
    if (roles && !roles.includes(user.role)) { window.location.href = DASH[user.role]; throw new Error("redirect"); }

    const sidebar = el("aside", { class: "sidebar" },
      el("div", { class: "top" }, el("div", { class: "brand" }, "Aura", el("span", {}, "Task")),
        el("button", { class: "btn sm menu-toggle", "aria-label": "Toggle menu", onclick: () => sidebar.classList.toggle("open") }, "Menu")),
      el("nav", { class: "nav", "aria-label": "Main" }, NAV.filter((n) => n.roles.includes(user.role)).map((n) =>
        el("a", { href: n.href(user.role), "aria-current": n.key === page ? "page" : null }, n.label(user.role)))),
      el("div", { class: "me" }, el("strong", {}, user.name), el("span", {}, user.role),
        el("div", { style: "margin-top:.5rem" }, el("button", { class: "btn sm", onclick: logout }, "Log out"))));
    const main = el("main", { class: "main", id: "main" });
    document.getElementById("app").replaceChildren(el("div", { class: "shell" }, sidebar, main));
    return { user, main };
  }

  const pageHead = (title, subtitle, ...actions) =>
    el("div", { class: "page-head" }, el("div", {}, el("h1", {}, title), subtitle ? el("p", { class: "muted" }, subtitle) : null),
      el("div", { class: "row" }, actions));

  return { init, pageHead, DASH };
})();
