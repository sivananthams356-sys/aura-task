(function () {
  const { el } = UI;
  if (Api.token() && Api.user()) { window.location.href = Layout.DASH[Api.user().role]; return; }

  const banner = el("div", { class: "form-error", role: "alert" });
  const email = el("input", { id: "email", type: "email", autocomplete: "username", required: true });
  const password = el("input", { id: "password", type: "password", autocomplete: "current-password", required: true });
  const button = el("button", { class: "btn primary", type: "submit", style: "width:100%" }, "Sign in");
  if (new URLSearchParams(location.search).get("expired")) banner.textContent = "Your session expired. Please sign in again.";

  const form = el("form", { novalidate: true, onsubmit: async (ev) => {
    ev.preventDefault();
    banner.textContent = "";
    if (!email.value.trim() || !password.value) { banner.textContent = "Enter your email and password."; return; }
    button.disabled = true; button.textContent = "Signing in…";
    try {
      const res = await Api.post("/auth/login", { email: email.value.trim(), password: password.value });
      Api.setSession(res.data.access_token, res.data.user);
      window.location.href = Layout.DASH[res.data.user.role];
    } catch (e) {
      banner.textContent = UI.errorText(e);
      button.disabled = false; button.textContent = "Sign in";
    }
  } }, banner,
  el("div", { class: "field" }, el("label", { for: "email" }, "Email"), email),
  el("div", { class: "field" }, el("label", { for: "password" }, "Password"), password), button);

  document.getElementById("app").replaceChildren(el("div", { class: "login-wrap" }, el("div", { class: "card login-card" },
    el("h1", {}, "Aura Task"), el("p", { class: "muted" }, "AI-based employee task monitoring"), form,
    el("p", { class: "muted small", style: "margin-top:1rem" }, "Accounts are created by an administrator."))));
})();
