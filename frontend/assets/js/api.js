/* Centralised API helper. Every page talks to the backend only through this file. */
const Api = (() => {
  const TOKEN_KEY = "aura_token", USER_KEY = "aura_user";

  class ApiError extends Error {
    constructor(status, code, message, details) {
      super(message);
      this.status = status; this.code = code; this.details = details || {};
    }
  }

  const token = () => sessionStorage.getItem(TOKEN_KEY);
  const user = () => { try { return JSON.parse(sessionStorage.getItem(USER_KEY)); } catch (e) { return null; } };
  const setSession = (t, u) => { sessionStorage.setItem(TOKEN_KEY, t); sessionStorage.setItem(USER_KEY, JSON.stringify(u)); };
  const setUser = (u) => sessionStorage.setItem(USER_KEY, JSON.stringify(u));
  const clearSession = () => { sessionStorage.removeItem(TOKEN_KEY); sessionStorage.removeItem(USER_KEY); };

  function query(params) {
    const p = new URLSearchParams();
    Object.entries(params || {}).forEach(([k, v]) => { if (v !== null && v !== undefined && v !== "") p.set(k, v); });
    const s = p.toString();
    return s ? "?" + s : "";
  }

  async function send(method, path, { body, params } = {}) {
    const headers = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (token()) headers["Authorization"] = "Bearer " + token();
    try {
      return await fetch(window.AURA_CONFIG.API_BASE_URL + path + query(params),
        { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
    } catch (e) {
      throw new ApiError(0, "NETWORK_ERROR", "Cannot reach the server. Is the backend running?");
    }
  }

  async function fail(res, path) {
    let json = null;
    try { json = await res.json(); } catch (e) { /* not JSON */ }
    if (res.status === 401 && !path.startsWith("/auth/login")) {
      clearSession();
      window.location.href = "login.html?expired=1";
    }
    const err = (json && json.error) || {};
    throw new ApiError(res.status, err.code || "ERROR", err.message || "Request failed", err.details);
  }

  async function request(method, path, opts) {
    const res = await send(method, path, opts);
    if (!res.ok) await fail(res, path);
    return res.json();            // { data, meta? }
  }

  async function download(path, fallbackName) {
    const res = await send("GET", path);
    if (!res.ok) await fail(res, path);
    const blob = await res.blob();
    const match = /filename="?([^"]+)"?/.exec(res.headers.get("Content-Disposition") || "");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = match ? match[1] : fallbackName;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  return {
    ApiError, token, user, setSession, setUser, clearSession, download,
    get: (path, params) => request("GET", path, { params }),
    post: (path, body) => request("POST", path, { body: body === undefined ? {} : body }),
    patch: (path, body) => request("PATCH", path, { body }),
  };
})();
