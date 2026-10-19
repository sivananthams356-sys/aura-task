(function () {
  const { el } = UI;
  const { user, main } = Layout.init({ page: "profile" });
  const nameF = UI.buildFields([{ name: "name", label: "Full name", required: true, value: user.name }]);
  const pwF = UI.buildFields([
    { name: "current_password", label: "Current password", type: "password", required: true, autocomplete: "current-password" },
    { name: "new_password", label: "New password", type: "password", required: true, autocomplete: "new-password", hint: "At least 10 characters with a letter and a number." }]);

  const nameForm = el("form", { class: "card", novalidate: true, onsubmit: async (ev) => {
    ev.preventDefault(); const v = nameF.check(); if (!v) return;
    try { const res = await Api.patch("/auth/me", v); Api.setUser(res.data); UI.toast("Profile updated", "success"); }
    catch (e) { nameF.showError(e); }
  } }, el("h2", {}, "Your details"),
  el("dl", { class: "kv" }, el("dt", {}, "Email"), el("dd", {}, user.email), el("dt", {}, "Role"), el("dd", {}, UI.badge(user.role)), el("dt", {}, "Member since"), el("dd", {}, UI.fmtDate(user.created_at))),
  el("div", { style: "margin-top:1rem" }), nameF.banner, nameF.nodes, el("button", { class: "btn primary", type: "submit" }, "Save name"));

  const pwForm = el("form", { class: "card", novalidate: true, onsubmit: async (ev) => {
    ev.preventDefault(); const v = pwF.check(); if (!v) return;
    try { await Api.post("/auth/change-password", v); UI.toast("Password changed", "success"); pwForm.reset(); }
    catch (e) { pwF.showError(e); }
  } }, el("h2", {}, "Change password"), pwF.banner, pwF.nodes, el("button", { class: "btn primary", type: "submit" }, "Change password"));

  main.append(Layout.pageHead("Profile and account"), el("div", { class: "grid cols-2" }, nameForm, pwForm));
})();
