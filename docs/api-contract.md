# Aura Task: API Contract (v1)

Single source of truth. Backend and frontend must use these exact paths and field names. Any change here must be applied to both sides.

## 1. Global Conventions

| Item | Rule |
|---|---|
| Base URL | `http://127.0.0.1:5000/api/v1` (frontend reads it from `assets/js/config.js`) |
| Format | JSON, `Content-Type: application/json` (CSV exports excepted) |
| Auth | `Authorization: Bearer <access_token>` on every endpoint except `POST /auth/login` |
| Dates | ISO 8601. Date-only fields: `YYYY-MM-DD`. Timestamps: UTC, `YYYY-MM-DDTHH:MM:SSZ` |
| Field names | `snake_case` everywhere |
| IDs | integers |
| Pagination | query `page` (default 1), `per_page` (default 20, max 100) |

**Success envelope**
```json
{ "data": <object | array>, "meta": { "page": 1, "per_page": 20, "total": 57, "pages": 3 } }
```
`meta` appears only on paginated lists.

**Error envelope** (same shape for all errors; never includes stack traces or server paths)
```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Human-readable summary", "details": { "progress": "Must be between 0 and 100" } } }
```

| HTTP | `code` | When |
|---|---|---|
| 400 | `BAD_REQUEST` | Malformed JSON |
| 401 | `UNAUTHORIZED` | Missing, invalid, expired, or revoked token; bad credentials |
| 403 | `FORBIDDEN` | Role or ownership check failed; account deactivated |
| 404 | `NOT_FOUND` | Missing resource (also returned when the caller may not know it exists) |
| 409 | `CONFLICT` | Duplicate email, invalid state transition |
| 413 | `PAYLOAD_TOO_LARGE` | Code over size limit |
| 422 | `VALIDATION_ERROR` | Field validation failed |
| 429 | `RATE_LIMITED` | Too many requests (stretch feature) |
| 500 | `INTERNAL_ERROR` | Generic message only |

**Enumerations**
- `role`: `admin`, `manager`, `employee`
- `priority`: `Low`, `Medium`, `High`, `Critical`
- `status`: `Pending`, `In Progress`, `Under Review`, `Completed`, `Blocked`
- `risk_category`: `Low`, `Medium`, `High`
- `severity`: `info`, `low`, `medium`, `high`, `critical`
- `method`: `ml_model`, `rule_based`

**Status transitions (enforced by backend, otherwise 409 `INVALID_TRANSITION`)**

| From | To | Who | Via |
|---|---|---|---|
| Pending | In Progress | assignee, manager, admin | `POST /tasks/{id}/status` |
| In Progress | Blocked | assignee, manager | `POST /tasks/{id}/status` |
| Blocked | In Progress | assignee, manager | `POST /tasks/{id}/status` |
| In Progress | Under Review | assignee (progress >= 90) | `POST /tasks/{id}/submit` |
| Under Review | Completed | task's manager | `POST /tasks/{id}/review` (approve) |
| Under Review | In Progress | task's manager (`rejection_count` + 1, feedback required) | `POST /tasks/{id}/review` (reject) |
| Completed | In Progress | task's manager, admin (`reopen_count` + 1) | `POST /tasks/{id}/reopen` |

Rules: progress 0 to 100 integer. Approving sets progress 100 and `completed_at`. Cannot set `Under Review` or `Completed` through `/status`.

**Object shapes**

`User`
```json
{ "id": 3, "name": "Priya S", "email": "priya@example.com", "role": "employee", "manager_id": 2, "is_active": true, "created_at": "2026-10-18T09:00:00Z" }
```

`Project`
```json
{ "id": 1, "name": "Website Revamp", "description": "...", "is_archived": false, "created_by": 1, "member_ids": [2, 3], "created_at": "..." }
```

`Task`
```json
{
  "id": 12, "title": "Build login API", "description": "...",
  "project_id": 1, "project_name": "Website Revamp",
  "assignee_id": 3, "assignee_name": "Priya S",
  "manager_id": 2, "manager_name": "Arun K",
  "priority": "High", "status": "In Progress", "progress": 40,
  "start_date": "2026-10-10", "deadline": "2026-10-25", "completed_at": null,
  "estimated_hours": 16.0, "actual_hours": 6.5,
  "review_feedback": null, "rejection_count": 0, "reopen_count": 0,
  "last_progress_update": "2026-10-17T11:00:00Z",
  "is_overdue": false, "is_archived": false,
  "created_by": 2, "created_at": "...", "updated_at": "..."
}
```
`is_overdue` is computed by the backend (deadline passed and status not `Completed`).

---

## 2. Authentication

### POST `/auth/login`
Role: public.
Request:
```json
{ "email": "priya@example.com", "password": "secret" }
```
200:
```json
{ "data": { "access_token": "<jwt>", "token_type": "Bearer", "expires_in": 3600, "user": { /* User */ } } }
```
Errors: 401 `INVALID_CREDENTIALS` (one generic message for wrong email or password), 403 `ACCOUNT_DEACTIVATED`, 422.
Validation: `email` valid format, `password` non-empty.

### POST `/auth/logout`
Role: any authenticated. Revokes the current token (server-side blocklist).
200: `{ "data": { "message": "Logged out" } }`

### GET `/auth/me`
Role: any. 200: `{ "data": { /* User */ } }`

### PATCH `/auth/me`
Role: any. Request: `{ "name": "New Name" }` (name only, 2 to 100 chars). 200: `{ "data": { /* User */ } }`

### POST `/auth/change-password`
Role: any.
Request: `{ "current_password": "...", "new_password": "..." }`
Validation: new password at least 10 chars, includes letter and number, differs from current.
200: `{ "data": { "message": "Password updated" } }`. Errors: 401 `INVALID_CREDENTIALS`, 422.

---

## 3. Users (admin; manager read-only on own team)

### GET `/users`
Role: admin (all), manager (own team only, forced filter). Employee: 403.
Query: `role`, `is_active` (true/false), `q` (name/email search), `page`, `per_page`.
200: `{ "data": [User...], "meta": {...} }`

### POST `/users`
Role: admin.
Request:
```json
{ "name": "Priya S", "email": "priya@example.com", "password": "TempPass123", "role": "employee", "manager_id": 2 }
```
Validation: unique email; `role` in enum; `manager_id` required for `employee` and must reference an active manager; password rules as above.
201: `{ "data": { /* User */ } }`. Errors: 409 `EMAIL_EXISTS`, 422.

### GET `/users/{id}`
Role: admin; manager (own team); any user for self. 200: `{ "data": User }`

### PATCH `/users/{id}`
Role: admin. Any of: `name`, `role`, `manager_id`. Email changes not allowed in v1. 200: `{ "data": User }`

### POST `/users/{id}/deactivate` and `/users/{id}/activate`
Role: admin. No body. Admin cannot deactivate themselves (409 `CANNOT_DEACTIVATE_SELF`). Deactivation revokes login.
200: `{ "data": User }`

### POST `/users/{id}/reset-password`
Role: admin. Request: `{ "new_password": "..." }`. 200: `{ "data": { "message": "Password reset" } }`

---

## 4. Projects

### GET `/projects`
Role: admin (all); manager and employee (projects they are members of). Query: `is_archived`, `q`, `page`, `per_page`.
200: `{ "data": [Project...], "meta": {...} }`

### POST `/projects`
Role: admin. Request: `{ "name": "...", "description": "...", "member_ids": [2, 3] }`
Validation: name 2 to 120 chars, unique; members exist and are active.
201: `{ "data": Project }`

### GET `/projects/{id}`
Role: admin; members. 200: `{ "data": Project }`

### PATCH `/projects/{id}`
Role: admin. Fields: `name`, `description`, `member_ids` (replaces list). 200: `{ "data": Project }`

### POST `/projects/{id}/archive`
Role: admin. 200: `{ "data": Project }`

---

## 5. Tasks

### GET `/tasks`
Role scoping applied by backend: admin all; manager their team's tasks; employee only own.
Query: `status`, `priority`, `project_id`, `assignee_id` (admin/manager), `overdue` (true), `q` (title search), `sort` (`deadline`, `priority`, `created_at`, `progress`, prefix `-` for descending, default `deadline`), `is_archived`, `page`, `per_page`.
200: `{ "data": [Task...], "meta": {...} }`

### POST `/tasks`
Role: manager (assignee must be on own team), admin.
Request:
```json
{
  "title": "Build login API", "description": "...", "project_id": 1, "assignee_id": 3,
  "priority": "High", "start_date": "2026-10-10", "deadline": "2026-10-25", "estimated_hours": 16
}
```
Validation: title 3 to 150 chars; assignee is active employee and project member; `deadline >= start_date`; `estimated_hours` > 0 and <= 500; priority in enum. For managers, `manager_id` is set to themselves; for admins it is the assignee's manager.
201: `{ "data": Task }` (status `Pending`, progress 0). Errors: 403 (assignee not on team), 422.

### GET `/tasks/{id}`
Role: admin; the task's manager; the assignee. 200: `{ "data": Task }`

### PATCH `/tasks/{id}`
Role: manager (own team), admin. Fields allowed: `title`, `description`, `priority`, `deadline`, `start_date`, `estimated_hours`, `assignee_id`. Cannot edit `Completed` tasks (409). Employee: 403.
200: `{ "data": Task }`

### POST `/tasks/{id}/archive`
Role: manager (own team), admin. No hard deletes. 200: `{ "data": Task }`

### POST `/tasks/{id}/progress`
Role: assignee only.
Request: `{ "progress": 60, "actual_hours": 9.5, "note": "API routes done" }`
Validation: `progress` integer 0 to 100; `actual_hours` >= 0 optional; `note` optional, up to 1000 chars. Allowed only when status is `In Progress` (409 otherwise). Progress must not exceed 99 until reviewed. Updates `last_progress_update`.
200: `{ "data": Task }`

### POST `/tasks/{id}/status`
Role: assignee, manager (own team). Request: `{ "status": "Blocked", "reason": "Waiting on API keys" }`
Only transitions in the table above. `reason` required for `Blocked`.
200: `{ "data": Task }`. Error: 409 `INVALID_TRANSITION`.

### POST `/tasks/{id}/submit`
Role: assignee. Request: `{ "note": "Ready for review" }` (optional). Requires status `In Progress` and progress >= 90.
200: `{ "data": Task }` (status `Under Review`)

### POST `/tasks/{id}/review`
Role: the task's manager only (admins view, do not review).
Request:
```json
{ "decision": "approve", "feedback": "Good work" }
```
`decision`: `approve` or `reject`. `feedback` required (3 to 1000 chars) on reject. Requires status `Under Review`.
200: `{ "data": Task }`

### POST `/tasks/{id}/reopen`
Role: manager (own team), admin. Request: `{ "reason": "Bug found in production" }` (required). Requires status `Completed`.
200: `{ "data": Task }`

### GET `/tasks/{id}/history`
Role: same visibility as the task. Query: `page`, `per_page`.
200:
```json
{ "data": [ { "id": 88, "task_id": 12, "actor_id": 3, "actor_name": "Priya S", "action": "progress_updated", "field": "progress", "old_value": "40", "new_value": "60", "created_at": "..." } ], "meta": {...} }
```
`action` values: `created`, `updated`, `assigned`, `progress_updated`, `status_changed`, `submitted`, `approved`, `rejected`, `reopened`, `archived`.

### GET `/tasks/{id}/comments`
Role: same visibility as the task. 200: `{ "data": [ { "id": 5, "task_id": 12, "author_id": 3, "author_name": "Priya S", "body": "...", "created_at": "..." } ] }`

### POST `/tasks/{id}/comments`
Role: same visibility as the task. Request: `{ "body": "Started on the routes" }` (1 to 1000 chars). 201: `{ "data": Comment }`

---

## 6. Dashboard

### GET `/dashboard/stats`
Role: any; the backend scopes data (admin: everything, manager: team, employee: own).
200:
```json
{
  "data": {
    "scope": "team",
    "tasks": { "total": 40, "pending": 8, "in_progress": 15, "under_review": 4, "completed": 10, "blocked": 3, "overdue": 5 },
    "by_priority": { "Low": 5, "Medium": 18, "High": 12, "Critical": 5 },
    "risk_distribution": { "Low": 20, "Medium": 9, "High": 6, "unscored": 5 },
    "upcoming_deadlines": [ { "task_id": 12, "title": "...", "deadline": "2026-10-25", "assignee_name": "Priya S" } ],
    "pending_reviews": 4,
    "users": { "total": 12, "active": 11 }
  }
}
```
`users` is returned for admin only. `pending_reviews` is returned for manager only.

---

## 7. Delay-Risk Predictions

Every response carries a `method` and a `disclaimer` so the UI cannot present a rule-based estimate as ML.

`Prediction`
```json
{
  "task_id": 12, "risk_category": "High", "risk_score": 0.78, "method": "ml_model",
  "model_version": "rf-synthetic-2026-10-18",
  "factors": [ { "feature": "days_since_last_update", "value": 6, "effect": "increases_risk", "reason": "No progress update for 6 days" } ],
  "suggested_actions": ["Check progress with the assignee", "Review the assignee's workload"],
  "predicted_at": "2026-10-18T10:00:00Z",
  "disclaimer": "Trained on synthetic demo data. Not evidence of real-world accuracy."
}
```
For `rule_based`: `risk_score` is `null` and the disclaimer reads "Rule-based estimate, not a trained ML prediction."

### GET `/predictions/tasks/{id}`
Role: admin; the task's manager; the assignee. Returns the latest stored prediction, or computes one if none exists. Completed or archived tasks: 409 `NOT_PREDICTABLE`.
200: `{ "data": Prediction }`

### POST `/predictions/run`
Role: manager (team), admin (all). Re-scores open tasks in scope.
Request: `{ "task_ids": [12, 13] }` (optional; omit to score all open tasks in scope).
200: `{ "data": { "scored": 14, "predictions": [Prediction...] } }`

### GET `/predictions`
Role: admin (all), manager (team). Employee: 403. Query: `risk_category`, `project_id`, `page`, `per_page`. Latest prediction per open task.
200: `{ "data": [Prediction + { "title", "assignee_name", "deadline" }...], "meta": {...} }`

### GET `/predictions/model-info`
Role: admin, manager.
200:
```json
{ "data": { "model_available": true, "trained_on": "synthetic", "model_version": "...", "trained_at": "...",
  "metrics": { "precision": 0.0, "recall": 0.0, "f1": 0.0, "roc_auc": 0.0, "baseline_f1": 0.0 },
  "notes": "Metrics measured on synthetic held-out data." } }
```
(Numbers shown are placeholders in this contract. Real values come from the training run in Phase 7.)

---

## 8. Code Analysis

### POST `/analysis/python`
Role: any authenticated. Static analysis only; code is never executed.
Request:
```json
{ "filename": "utils.py", "code": "import os\nprint('hi')\n", "task_id": 12 }
```
Validation: `code` string, non-empty, <= 50,000 bytes (UTF-8) and <= 2,000 lines (else 413 `PAYLOAD_TOO_LARGE`); `filename` optional, 1 to 100 chars, letters/digits/`._-` only (used for display, never as a file path); `task_id` optional and must be visible to the caller.
201:
```json
{
  "data": {
    "id": 7, "filename": "utils.py", "language": "python", "line_count": 2,
    "submitted_by": 3, "created_at": "...",
    "summary": { "total": 2, "critical": 0, "high": 0, "medium": 1, "low": 1, "info": 0 },
    "syntax_valid": true,
    "findings": [
      { "id": 21, "rule_id": "F401", "severity": "low", "category": "unused_code", "line": 1,
        "message": "`os` imported but unused",
        "explanation": "Unused imports add clutter and can hide real dependencies.",
        "suggestion": "Remove the import.", "tool": "ruff" }
    ],
    "disclaimer": "Static analysis cannot detect every logical bug. These are not ML predictions."
  }
}
```
Syntax errors return 201 with `syntax_valid: false` and one finding (`rule_id: "SYNTAX"`, `severity: "critical"`). `tool` is one of `ast`, `ruff`, `pylint`.

### GET `/analysis/reports`
Role: admin (all), manager (own team's members), employee (own). Query: `submitted_by` (admin/manager), `page`, `per_page`.
200: `{ "data": [ { "id", "filename", "submitted_by", "submitted_by_name", "line_count", "summary", "created_at" } ], "meta": {...} }`

### GET `/analysis/reports/{id}`
Role: same scoping as above. Query: `severity` (optional filter). 200: same shape as the POST response `data`.

---

## 9. Reports

### GET `/reports/summary`
Role: admin (all), manager (team). Employee gets own-only data. Query: `from`, `to` (dates, optional; default last 30 days).
200:
```json
{
  "data": {
    "range": { "from": "2026-09-18", "to": "2026-10-18" },
    "totals": { "total": 40, "pending": 8, "in_progress": 15, "under_review": 4, "completed": 10, "blocked": 3, "overdue": 5 },
    "by_priority": { "Low": 5, "Medium": 18, "High": 12, "Critical": 5 },
    "by_employee": [ { "user_id": 3, "name": "Priya S", "total": 8, "completed": 3, "overdue": 1 } ],
    "completion_trend": [ { "date": "2026-10-01", "completed": 2 } ],
    "rejection_trend": [ { "date": "2026-10-01", "rejections": 1, "reopenings": 0 } ],
    "risk_distribution": { "Low": 20, "Medium": 9, "High": 6, "unscored": 5 },
    "analysis_by_severity": { "critical": 1, "high": 3, "medium": 8, "low": 12, "info": 2 }
  }
}
```
`by_employee` is omitted for employees.

### GET `/reports/export/tasks.csv`
Role: admin, manager (team scope). Response: `Content-Type: text/csv`, `Content-Disposition: attachment; filename="tasks.csv"`. Columns: `id,title,project,assignee,manager,priority,status,progress,deadline,is_overdue,rejection_count,reopen_count`. Cells beginning with `=`, `+`, `-`, `@` are prefixed with `'` to prevent spreadsheet formula injection.

### GET `/reports/export/analysis.csv`
Role: admin, manager (team scope). Columns: `report_id,filename,submitted_by,created_at,rule_id,severity,category,line,tool`.

---

## 10. Endpoint Index

| Method | Path | Roles |
|---|---|---|
| POST | /auth/login | public |
| POST | /auth/logout | any |
| GET, PATCH | /auth/me | any |
| POST | /auth/change-password | any |
| GET, POST | /users | admin, manager (GET team) |
| GET | /users/{id} | admin, manager (team), self |
| PATCH | /users/{id} | admin |
| POST | /users/{id}/activate, /deactivate, /reset-password | admin |
| GET, POST | /projects | any (scoped), admin (POST) |
| GET | /projects/{id} | admin, members |
| PATCH | /projects/{id} | admin |
| POST | /projects/{id}/archive | admin |
| GET, POST | /tasks | scoped, manager/admin (POST) |
| GET | /tasks/{id} | admin, manager, assignee |
| PATCH | /tasks/{id} | manager, admin |
| POST | /tasks/{id}/archive | manager, admin |
| POST | /tasks/{id}/progress | assignee |
| POST | /tasks/{id}/status | assignee, manager |
| POST | /tasks/{id}/submit | assignee |
| POST | /tasks/{id}/review | task's manager |
| POST | /tasks/{id}/reopen | manager, admin |
| GET | /tasks/{id}/history | task visibility |
| GET, POST | /tasks/{id}/comments | task visibility |
| GET | /dashboard/stats | any (scoped) |
| GET | /predictions | admin, manager |
| GET | /predictions/tasks/{id} | admin, manager, assignee |
| POST | /predictions/run | admin, manager |
| GET | /predictions/model-info | admin, manager |
| POST | /analysis/python | any |
| GET | /analysis/reports, /analysis/reports/{id} | scoped |
| GET | /reports/summary | any (scoped) |
| GET | /reports/export/tasks.csv, /analysis.csv | admin, manager |

---

## 11. Implementation Notes (changes made while building; these override the sections above)

- **Reopen:** `POST /tasks/{id}/reopen` sets `progress` to 90 (so the task can be re-submitted) and stores the reason in `review_feedback`.
- **Progress cap:** `POST /tasks/{id}/progress` accepts 0 to 100 syntactically, but 100 returns 422 ("only after manager approval").
- **Hidden resources return 404, not 403**, when the caller is not allowed to know a task, report, project or user exists. 403 is used for role failures and wrong-team actions on visible items.
- **Analysis report** (`POST /analysis/python` and `GET /analysis/reports/{id}`) additionally returns: `code` (the submitted text), `tools_used` (list, e.g. `["ast","ruff"]`) and `notes` (list; for example "Ruff is not installed; only built-in checks were run"). Without Ruff only the built-in AST rules run.
- **Report scope:** a manager sees reports submitted by their team members and themselves.
- **`GET /reports/summary`:** `from`/`to` limit only `completion_trend` and `rejection_trend`; totals, priority, risk and severity figures cover all authorised data.
- **Predictions:** `GET /predictions/tasks/{id}` re-computes automatically if the task changed since the stored prediction. `risk_score` is a model score, not a calibrated probability. `GET /predictions` returns only tasks that already have a stored prediction (use `POST /predictions/run` first).
- **Optional body:** `POST /tasks/{id}/submit` and `POST /predictions/run` accept an empty or missing body.
- **Extra endpoint:** `GET /api/v1/health` returns `{"data":{"status":"ok"}}` (no auth) for connectivity checks.
- **Project members** are stored in an association table with a composite primary key (`project_id`, `user_id`).
