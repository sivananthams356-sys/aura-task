# Testing

## Automated tests (pytest)
Run from the `backend` folder with the virtual environment active:
```powershell
pytest -v
```
| File | Covers |
|---|---|
| `test_auth.py` | login, hashing, token errors, logout revocation, deactivated accounts, password change, user creation rules |
| `test_permissions.py` | role checks, team scoping, ownership, review rights, 404 for hidden resources |
| `test_tasks.py` | create/validate, full workflow with history, invalid transitions, filters, archive, dashboard scoping, CSV export, report shape |
| `test_analysis_api.py` | structured findings, syntax errors, malformed/oversized input, code never executed, no path leaks, report scoping |
| `test_ai_api.py` | prediction endpoint, honest labels, list/run, completed tasks, error format consistency |
| `test_ai_unit.py` | feature building, missing/garbage values, fallback, synthetic data, training metrics, inference, corrupt model |
| `test_analysis_unit.py` | AST rules, no false alarm inside try, deeply nested input, tool notes |

## What was actually verified while this project was generated
The generation environment had no internet, so Flask, Flask-SQLAlchemy and pytest could not be installed there.
- `test_ai_unit.py` and `test_analysis_unit.py` (14 tests) were run with a small stand-in runner and **passed**.
- All Python files compile and all frontend JavaScript passes `node --check`.
- The Flask API tests (`test_auth.py`, `test_permissions.py`, `test_tasks.py`, `test_analysis_api.py`, `test_ai_api.py`) were **written but not run**. Run `pytest -v` on your machine; if anything fails, send the output so it can be fixed.

## Manual integration test (three roles)
Prepare: backend running, frontend served, demo data seeded (see the root README).

**Admin**
1. Log in as the admin you created. You land on the Admin Dashboard with real counts.
2. Users: create a manager and an employee (employee needs a manager). Deactivate then reactivate one.
3. Projects: create a project and add the manager and employee.
4. Tasks: you can see all tasks but there is no Approve button.
5. Reports: change the date range; export both CSV files; open one in a spreadsheet.

**Manager** (`demo.manager@example.com`)
1. Dashboard shows team numbers and "waiting for your review".
2. New task: assign to an employee. Try assigning to someone outside your team (not possible in the list).
3. Delay Risk: click "Score all open tasks"; open a task and read the reasons. Confirm the method label is shown.
4. Task Reviews: reject one with feedback, approve another. Reopen a completed task.
5. Code Analysis: submit code; open results; filter by severity.

**Employee** (`demo.employee1@example.com`)
1. Only your own tasks are listed; change `?id=` in a task URL to another employee's task and confirm a "not found" error.
2. Start a task, update progress, try 100 (rejected), reach 90+, submit for review.
3. Add a comment; see it in history.
4. Code Analysis: submit code with `eval(...)` and a bare `except:`; check severity, explanation and suggestion; paste an invalid snippet and see the syntax error.
5. Log out; press Back and confirm protected pages send you to login.
