# Aura Task: Backend (Flask API)

Setup and run commands are in the root `README.md`. API reference: `../docs/api-contract.md`.

Useful commands (run in `backend` with the venv active):
```powershell
flask --app run init-db          # create tables
flask --app run create-admin     # first admin (interactive)
flask --app run seed-demo        # DEMO users + tasks (delete before deployment)
flask --app run train-model      # train delay-risk model on SYNTHETIC data
flask --app run run --debug      # start API on :5000
pytest -v                        # run tests
```
Schema changes: see "Schema updates" in `../docs/architecture.md` (Flask-Migrate).
