# Aura Task: Frontend

Static HTML/CSS/JS. No build step.

```powershell
cd frontend
py -m http.server 5500
```
Open http://127.0.0.1:5500/login.html. The backend address is set in `assets/js/config.js`.

Files: `assets/js/api.js` (the only code that calls the API), `ui.js` (safe DOM helpers, forms, toasts), `layout.js` (role-based navigation), and one script per page. All user text is rendered with `textContent`.
