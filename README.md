# Aura Task: AI-Based Employee Task Monitoring and Human Error Prediction System

Final-year CSE project. Two separate applications that talk through a documented REST API.

| Part | Tech | Folder |
|---|---|---|
| Frontend | HTML5, CSS3, vanilla JavaScript (Fetch API) | `frontend/` |
| Backend | Python, Flask, Flask-SQLAlchemy, SQLite, Flask-JWT-Extended, scikit-learn, Ruff, pytest | `backend/` |
| Docs | API contract, architecture, schema, testing | `docs/` |

**Roles:** Admin (users, projects, everything read-only on tasks), Manager (own team, tasks, reviews, risk), Employee (own tasks, progress, code analysis). All permissions are enforced by the backend.

**Honesty notes:** the delay-risk model is trained on **synthetic** data, so its metrics show the pipeline works, not real-world accuracy. Code analysis is **rule-based static analysis**, not ML. Submitted code is **never executed**. See `docs/architecture.md`.

## Folder tree
```
aura-task/
├── README.md
├── docs/            api-contract.md, architecture.md, database-schema.md, testing.md
├── backend/
│   ├── run.py  config.py  requirements.txt  .env.example  pytest.ini
│   ├── app/  (routes, models, services, schemas, security, ai, analysis, cli.py)
│   ├── tests/
│   └── instance/    (SQLite file is created here)
└── frontend/        login.html, 3 dashboards, users, projects, tasks, task-*, risk, code analysis, reports, profile
    └── assets/      css/ and js/
```

## Setup on Windows (PowerShell)

You need Python 3.11 or 3.12 (`py --version`). Open PowerShell in the folder that contains `aura-task`.

### 1. Backend (Terminal 1)
```powershell
cd aura-task\backend
py -m venv venv
.\venv\Scripts\Activate.ps1
```
If PowerShell blocks the activate script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then try again.
```powershell
pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
python -c "import secrets; print(secrets.token_hex(32))"
```
Open `backend\.env` in an editor and paste the two different values after `SECRET_KEY=` and `JWT_SECRET_KEY=`.
```powershell
flask --app run init-db
flask --app run create-admin
flask --app run seed-demo
flask --app run train-model
flask --app run run --debug
```
- `create-admin` asks for your name, email and a password you choose (10+ characters, letter and number). There is no built-in admin account.
- `seed-demo` creates a demo manager, two demo employees, a project and sample tasks, and **prints one random password once. Copy it.**
- `train-model` retrains the delay-risk model with your installed scikit-learn version (a pre-trained file is included, but retraining avoids version warnings).
- The API now runs at http://127.0.0.1:5000. Check http://127.0.0.1:5000/api/v1/health.

### 2. Frontend (Terminal 2)
```powershell
cd aura-task\frontend
py -m http.server 5500
```
Open **http://127.0.0.1:5500/login.html** (use `127.0.0.1` or `localhost`, which are the origins allowed by CORS). If your backend uses another address, edit `frontend\assets\js\config.js`.

### 3. Run the tests
```powershell
cd aura-task\backend
.\venv\Scripts\Activate.ps1
pytest -v
```

## Before real deployment
Delete or deactivate the three `demo.*@example.com` accounts and the "Demo Project" data, use fresh secrets, serve the API with a production server (for example Waitress) behind HTTPS, and restrict `CORS_ORIGINS` to your real frontend address.

## Demo script (about 10 minutes)
1. **Intro (1 min):** problem, three roles, architecture diagram from `docs/architecture.md`; stress transparent monitoring (no keystrokes, no screenshots).
2. **Admin (2 min):** log in, dashboard numbers, create a user, create a project and add members, show Reports and download the CSV.
3. **Manager (3 min):** dashboard; create and assign a task; **Delay Risk page: score all tasks**, open a high-risk task and read the reasons and suggested actions; point out the banner saying the model uses synthetic data.
4. **Employee (2 min):** only own tasks; start, update progress (try 100 and show the validation), submit for review.
5. **Review loop (1 min):** manager rejects with feedback, then approves; show task history and the rejection counter.
6. **Code analysis (1 min):** paste code with `eval`, a bare `except` and an unused import; show severity filter, line highlight, explanation and fix; paste a syntax error.
7. **Security and honesty (1 min):** try another employee's task URL (404), show the API contract and test run, explain synthetic data and what is needed to train on real data.

## Limitations
- Delay-risk model uses synthetic data; no real-world accuracy claim. Scores are not calibrated probabilities.
- Static analysis covers Python only and cannot detect every logical bug. Without Ruff installed only the built-in AST rules run.
- ML bug-risk prediction was not built (no labelled defect data); see `docs/architecture.md`.
- SQLite and the Flask development server are for development, not production load.
- Tokens are stored in `sessionStorage`; there is no refresh-token flow or login rate limiting.
- The Flask API tests were written but not run in the environment that generated the project (see `docs/testing.md`).

## Future enhancements
Real-data retraining pipeline, SHAP explanations, login rate limiting, email notifications, more languages for code analysis, MySQL deployment, httpOnly-cookie sessions with CSRF protection, Docker packaging.

## Troubleshooting
| Problem | Fix |
|---|---|
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `flask` not found | Activate the venv first (`.\venv\Scripts\Activate.ps1`) |
| Browser shows "Cannot reach the server" | Backend not running, or wrong `API_BASE_URL` in `config.js` |
| CORS error in browser console | Open the frontend as `http://127.0.0.1:5500` or `http://localhost:5500`, or add your origin to `CORS_ORIGINS` in `.env` |
| Logged out after every restart | `SECRET_KEY` / `JWT_SECRET_KEY` missing in `.env` |
| "Ruff is not installed" note in results | `pip install ruff` inside the venv |
| `ModuleNotFoundError: app` when running pytest | Run pytest from the `backend` folder |
| Want a clean database | Stop the server, delete `backend\instance\aura_task.db`, run `init-db`, `create-admin`, `seed-demo` again |
