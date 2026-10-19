/* Small UI toolkit. All dynamic text goes through textContent (el helper), so user-submitted
   text and code can never be interpreted as HTML. */
const UI = (() => {
  function append(node, children) {
    for (const c of children.flat(Infinity)) {
      if (c === null || c === undefined || c === false) continue;
      node.append(c.nodeType ? c : document.createTextNode(String(c)));
    }
  }

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
      else if (["value", "checked", "disabled", "selected"].includes(k)) node[k] = v;
      else node.setAttribute(k, v === true ? "" : v);
    }
    append(node, children);
    return node;
  }

  const slug = (s) => String(s).toLowerCase().replace(/\s+/g, "-");
  const badge = (text) => el("span", { class: "badge b-" + slug(text) }, text);
  const fmtDate = (d) => d ? new Date(d + (d.length === 10 ? "T00:00:00" : "")).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" }) : "—";
  const fmtDateTime = (d) => d ? new Date(d).toLocaleString() : "—";
  const progressBar = (pct) => el("div", { class: "progress", role: "progressbar", "aria-valuenow": pct, "aria-valuemin": 0, "aria-valuemax": 100, title: pct + "%" }, el("i", { style: "width:" + pct + "%" }));
  const loading = (text) => el("div", { class: "loading", role: "status" }, text || "Loading…");
  const empty = (title, hint) => el("div", { class: "empty" }, el("strong", {}, title), hint || "");
  const errorText = (e) => (e && e.message) || "Something went wrong";
  const errorBox = (e) => el("div", { class: "alert error", role: "alert" }, errorText(e));

  function toast(message, type) {
    let box = document.getElementById("toasts");
    if (!box) { box = el("div", { id: "toasts", role: "status", "aria-live": "polite" }); document.body.append(box); }
    const t = el("div", { class: "toast " + (type || "") }, message);
    box.append(t);
    setTimeout(() => t.remove(), 4500);
  }

  function table(columns, rows, emptyTitle, emptyHint) {
    if (!rows.length) return empty(emptyTitle || "Nothing here yet", emptyHint);
    return el("div", { class: "table-wrap" }, el("table", {},
      el("thead", {}, el("tr", {}, columns.map((c) => el("th", { scope: "col" }, c.label)))),
      el("tbody", {}, rows.map((r) => el("tr", {}, columns.map((c) => el("td", {}, c.render(r))))))));
  }

  function pager(meta, onPage) {
    if (!meta || meta.pages <= 1) return el("div");
    return el("div", { class: "pager" },
      el("span", { class: "muted small" }, `Page ${meta.page} of ${meta.pages} (${meta.total} items)`),
      el("button", { class: "btn sm", disabled: meta.page <= 1, onclick: () => onPage(meta.page - 1) }, "Previous"),
      el("button", { class: "btn sm", disabled: meta.page >= meta.pages, onclick: () => onPage(meta.page + 1) }, "Next"));
  }

  function bars(items) {
    const max = Math.max(1, ...items.map((i) => i.value));
    return el("div", { class: "bars" }, items.map((i) => el("div", { class: "bar-row" },
      el("span", {}, i.label),
      el("div", { class: "track" }, el("div", { class: "fill c-" + (i.tone || i.label), style: "width:" + (i.value / max) * 100 + "%" })),
      el("strong", {}, i.value))));
  }

  /* ---- forms ---- */
  function buildFields(fields) {
    const inputs = {}, errs = {};
    const nodes = fields.map((f) => {
      let input;
      const id = "f_" + f.name;
      if (f.type === "textarea") input = el("textarea", { id, rows: f.rows || 4 });
      else if (f.type === "select") {
        input = el("select", { id }, (f.options || []).map((o) => el("option", { value: o.value }, o.label)));
      } else if (f.type === "multiselect") {
        input = el("div", { class: "checklist", id }, (f.options || []).map((o) => el("label", { class: "check" },
          el("input", { type: "checkbox", value: String(o.value), checked: (f.value || []).includes(o.value) }), o.label)));
      } else input = el("input", { id, type: f.type || "text", autocomplete: f.autocomplete || "off" });
      if (f.type !== "multiselect") {
        if (f.value !== undefined && f.value !== null) input.value = f.value;
        if (f.disabled) input.disabled = true;
        if (f.min !== undefined) input.setAttribute("min", f.min);
        if (f.max !== undefined) input.setAttribute("max", f.max);
        if (f.step !== undefined) input.setAttribute("step", f.step);
      }
      inputs[f.name] = input;
      errs[f.name] = el("div", { class: "err", role: "alert" });
      return el("div", { class: "field" }, el("label", { for: id }, f.label + (f.required ? " *" : "")),
        input, f.hint ? el("div", { class: "muted small" }, f.hint) : null, errs[f.name]);
    });
    const banner = el("div", { class: "form-error", role: "alert" });

    function collect() {
      const out = {};
      for (const f of fields) {
        const i = inputs[f.name];
        let v;
        if (f.type === "multiselect") v = [...i.querySelectorAll("input:checked")].map((c) => Number(c.value));
        else if (f.type === "number" || f.numeric) v = i.value === "" ? null : Number(i.value);
        else v = f.type === "password" ? i.value : i.value.trim();
        if (v === "" || v === null) { if (f.required) out[f.name] = v; continue; }
        out[f.name] = v;
      }
      return out;
    }
    function clear() { banner.textContent = ""; Object.values(errs).forEach((e) => { e.textContent = ""; }); }
    function check() {
      clear();
      const values = collect();
      let ok = true;
      for (const f of fields) {
        const v = values[f.name];
        if (f.required && (v === undefined || v === null || v === "" || (Array.isArray(v) && !v.length))) {
          errs[f.name].textContent = "This field is required"; ok = false;
        }
      }
      return ok ? values : null;
    }
    function showError(e) {
      banner.textContent = UI.errorText(e);
      Object.entries(e.details || {}).forEach(([k, msg]) => { if (errs[k]) errs[k].textContent = msg; });
    }
    return { nodes, inputs, banner, collect, check, showError, clear };
  }

  function openForm({ title, intro, fields, submitText, onSubmit }) {
    const dlg = el("dialog", { "aria-label": title });
    const f = buildFields(fields);
    const submit = el("button", { class: "btn primary", type: "submit" }, submitText || "Save");
    const form = el("form", { novalidate: true, onsubmit: async (ev) => {
      ev.preventDefault();
      const values = f.check();
      if (!values) return;
      submit.disabled = true; submit.textContent = "Saving…";
      try { await onSubmit(values); dlg.close(); }
      catch (e) { f.showError(e); }
      finally { submit.disabled = false; submit.textContent = submitText || "Save"; }
    } }, el("h2", {}, title), intro ? el("p", { class: "muted" }, intro) : null, f.banner, f.nodes,
    el("div", { class: "dialog-actions" }, el("button", { class: "btn", type: "button", onclick: () => dlg.close() }, "Cancel"), submit));
    dlg.append(form);
    dlg.addEventListener("close", () => dlg.remove());
    document.body.append(dlg);
    dlg.showModal();
    const first = dlg.querySelector("input:not([type=checkbox]), select, textarea");
    if (first) first.focus();
  }

  function confirmDialog(message, confirmText) {
    return new Promise((resolve) => {
      const dlg = el("dialog", { "aria-label": "Confirm" });
      let answer = false;
      dlg.append(el("p", {}, message), el("div", { class: "dialog-actions" },
        el("button", { class: "btn", onclick: () => dlg.close() }, "Cancel"),
        el("button", { class: "btn danger", onclick: () => { answer = true; dlg.close(); } }, confirmText || "Confirm")));
      dlg.addEventListener("close", () => { dlg.remove(); resolve(answer); });
      document.body.append(dlg);
      dlg.showModal();
    });
  }

  /* Run an async action from a button: shows errors as toasts. */
  async function act(fn, successMessage) {
    try { await fn(); if (successMessage) toast(successMessage, "success"); return true; }
    catch (e) { toast(errorText(e), "error"); return false; }
  }

  return { el, badge, slug, fmtDate, fmtDateTime, progressBar, loading, empty, errorBox, errorText, toast, table, pager,
           bars, buildFields, openForm, confirmDialog, act };
})();
