# Aura Task: Architecture

```
Browser (frontend, static HTML/CSS/JS, :5500)  --Fetch + Bearer JWT-->  Flask API (:5000)
                                                                          routes -> services -> models -> SQLite
                                                                          app/ai       (delay-risk model + rule fallback)
                                                                          app/analysis (AST rules + Ruff, never executes code)
```

## Layers (backend)
| Layer | Folder | Responsibility |
|---|---|---|
| Routes | `app/routes` | HTTP only: parse, validate, call a service, return the standard envelope |
| Services | `app/services` | Business rules (status transitions, scoping, stats, predictions) |
| Models | `app/models` | SQLAlchemy tables |
| Security | `app/security` | `@auth_required(roles)`, JWT revocation handlers |
| AI | `app/ai` | Pure Python/scikit-learn, no Flask imports (easy to test and retrain) |
| Analysis | `app/analysis` | Pure Python static analysis, no Flask imports |

## Security design
- Passwords hashed with Werkzeug; JWT access tokens (60 min); logout stores the token id in a blocklist.
- Every protected route checks the token, the account is still active, the role, and ownership/team scope (`app/services/access.py`). Unknown-to-caller resources return 404.
- No default admin: `flask create-admin` prompts for credentials. Demo accounts come only from `flask seed-demo` with a random password.
- Secrets live in `.env` (git-ignored). CORS allows only the configured frontend origins.
- Submitted code is parsed with `ast` and passed to Ruff through stdin using an argument list (no shell), a fixed file label, a 10 s timeout. It is never imported or run. Size limits: 50 KB, 2,000 lines, no null bytes. Errors never contain tracebacks or server paths.
- The frontend builds all DOM with `textContent` (helper `UI.el`), so user text and code cannot inject HTML. Tokens are kept in `sessionStorage` (cleared when the tab closes). Trade-off: readable by injected JavaScript, which is why safe rendering matters; httpOnly cookies would need CSRF protection.
- No keystroke logging, screenshots, webcam or hidden monitoring. Only task data and code the employee chooses to submit.

## Delay-risk prediction: what is and is not claimed
- **Features** (computed at prediction time only, so no leakage): progress, days to deadline, priority, estimated hours, hours logged, assignee's open tasks, review rejections, reopenings, days since last update.
- **Training data is synthetic** (`app/ai/synthetic_data.py`). Labels come from a formula plus noise, so the model re-learns that formula. Reported metrics (precision, recall, F1, ROC-AUC, confusion matrix, baselines) prove the pipeline works, **not** real-world accuracy. The UI and API repeat this.
- **Model:** Random Forest, stratified 80/20 split, compared with a majority-class baseline and a simple deadline rule.
- **Explanations:** for each prediction, each feature is replaced by its typical (median) value and the change in score is shown. This is a simple, model-agnostic local explanation. SHAP was not used to avoid an extra dependency; `shap.TreeExplainer` is compatible with Random Forest if you want to add it later.
- **Fallback:** if no valid model file exists, a transparent points-based rule estimate is used. It is labelled `rule_based`, has no score, and is described as not a trained ML prediction.
- **Model file safety:** `joblib` files are loaded only from `app/ai/artifacts/`, never from uploads.

### Collecting real data ethically, then retraining
1. Tell employees what is recorded (task fields and timestamps already in the system) and why. Do not add hidden tracking.
2. Each time a task closes, store a snapshot of its features taken *before the outcome* (for example, 3 days before the deadline) plus the label "finished late: yes/no".
3. Keep the data minimal and access-controlled; use it for planning support, not for punishing individuals.
4. When enough real labelled snapshots exist (hundreds at least, with a reasonable number of late tasks), replace `synthetic_data.generate()` with a loader for that table, retrain, and re-evaluate on a time-based split.

## Code analysis vs. ML bug prediction
Static analysis (syntax, AST rules, Ruff) reports problems that exist in the text. It is rule-based and not machine learning. It cannot find every logical bug. The optional ML bug-risk predictor was **not built**: there is no labelled defect dataset, and inventing one would be misleading. A future version needs real data (commit history with bug-fix labels), defined features (complexity, churn, author experience), and honest evaluation.

## Moving from SQLite to MySQL
All access goes through SQLAlchemy and no SQLite-specific features are used. Install `pymysql`, set `DATABASE_URL=mysql+pymysql://user:password@localhost/aura_task_db` in `.env`, create the database, run `flask db upgrade` (or `flask init-db` for a fresh start). Datetimes are stored as UTC.

## Schema updates (migrations)
Flask-Migrate (Alembic) is wired in. After the first `flask db init`, change a model, run `flask db migrate -m "describe change"`, review the generated file in `migrations/versions`, then `flask db upgrade`. For a throw-away development database you can instead delete `instance/aura_task.db` and run `flask init-db`.
