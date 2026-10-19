from datetime import date, timedelta

from tests.helpers import task_payload


def _new(client, world, **overrides):
    res = client.post("/api/v1/tasks", headers=world["h"]["m1"], json=task_payload(world["p1"], world["e1"], **overrides))
    return res


def test_create_task_defaults_and_shape(client, world):
    res = _new(client, world)
    task = res.get_json()["data"]
    assert res.status_code == 201
    assert task["status"] == "Pending" and task["progress"] == 0 and task["manager_id"] == world["m1"].id
    assert task["assignee_name"] and task["project_name"] and task["is_overdue"] is False
    for key in ("rejection_count", "reopen_count", "last_progress_update", "estimated_hours", "is_archived"):
        assert key in task


def test_create_task_validation(client, world):
    bad = [{"title": "ab"}, {"priority": "Urgent"}, {"estimated_hours": 0}, {"estimated_hours": 9999},
           {"deadline": "2020-01-01", "start_date": "2026-01-01"}, {"deadline": "not-a-date"}, {"project_id": 99999}]
    for override in bad:
        res = _new(client, world, **override)
        assert res.status_code == 422, (override, res.get_json())
        assert res.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_full_review_workflow_with_history(client, world):
    task_id = _new(client, world).get_json()["data"]["id"]
    e1, m1 = world["h"]["e1"], world["h"]["m1"]
    url = f"/api/v1/tasks/{task_id}"
    assert client.post(url + "/progress", headers=e1, json={"progress": 10}).status_code == 409   # not started
    assert client.post(url + "/status", headers=e1, json={"status": "In Progress"}).status_code == 200
    assert client.post(url + "/progress", headers=e1, json={"progress": 101}).status_code == 422
    assert client.post(url + "/progress", headers=e1, json={"progress": -1}).status_code == 422
    assert client.post(url + "/progress", headers=e1, json={"progress": 100}).status_code == 422
    assert client.post(url + "/progress", headers=e1, json={"progress": 50, "actual_hours": 4, "note": "half"}).status_code == 200
    assert client.post(url + "/submit", headers=e1, json={}).status_code == 422                  # needs >= 90
    client.post(url + "/progress", headers=e1, json={"progress": 92})
    assert client.post(url + "/submit", headers=e1, json={}).get_json()["data"]["status"] == "Under Review"

    assert client.post(url + "/review", headers=m1, json={"decision": "reject"}).status_code == 422   # feedback needed
    rejected = client.post(url + "/review", headers=m1, json={"decision": "reject", "feedback": "Add tests"}).get_json()["data"]
    assert rejected["status"] == "In Progress" and rejected["rejection_count"] == 1
    assert rejected["review_feedback"] == "Add tests"

    client.post(url + "/progress", headers=e1, json={"progress": 98})
    client.post(url + "/submit", headers=e1, json={})
    done = client.post(url + "/review", headers=m1, json={"decision": "approve", "feedback": "Good"}).get_json()["data"]
    assert done["status"] == "Completed" and done["progress"] == 100 and done["completed_at"]
    assert client.patch(url, headers=m1, json={"title": "edit after done"}).status_code == 409

    reopened = client.post(url + "/reopen", headers=m1, json={"reason": "Bug found"}).get_json()["data"]
    assert reopened["status"] == "In Progress" and reopened["reopen_count"] == 1 and reopened["completed_at"] is None

    actions = [h["action"] for h in client.get(url + "/history", headers=m1).get_json()["data"]]
    for expected in ("created", "assigned", "progress_updated", "status_changed", "submitted", "rejected",
                     "approved", "reopened"):
        assert expected in actions
    assert any("half" in c["body"] for c in client.get(url + "/comments", headers=m1).get_json()["data"])


def test_invalid_status_transitions(client, world):
    task_id = _new(client, world).get_json()["data"]["id"]
    e1 = world["h"]["e1"]
    url = f"/api/v1/tasks/{task_id}/status"
    for target in ("Completed", "Under Review", "Pending"):
        assert client.post(url, headers=e1, json={"status": target}).status_code == 409
    assert client.post(url, headers=e1, json={"status": "Nonsense"}).status_code == 422
    client.post(url, headers=e1, json={"status": "In Progress"})
    assert client.post(url, headers=e1, json={"status": "Blocked"}).status_code == 422          # reason needed
    assert client.post(url, headers=e1, json={"status": "Blocked", "reason": "waiting"}).status_code == 200
    assert client.post(f"/api/v1/tasks/{task_id}/progress", headers=e1, json={"progress": 5}).status_code == 409


def test_filters_sorting_pagination_and_overdue(client, world):
    _new(client, world, title="Alpha task", priority="Low")
    _new(client, world, title="Beta task", priority="Critical", start_date="2020-01-01", deadline="2020-02-01")
    h = world["h"]["m1"]
    overdue = client.get("/api/v1/tasks?overdue=true", headers=h).get_json()["data"]
    assert [t["title"] for t in overdue] == ["Beta task"] and overdue[0]["is_overdue"] is True
    assert len(client.get("/api/v1/tasks?q=alpha", headers=h).get_json()["data"]) == 1
    by_priority = client.get("/api/v1/tasks?sort=-priority", headers=h).get_json()["data"]
    assert by_priority[0]["priority"] == "Critical"
    page = client.get("/api/v1/tasks?per_page=1&page=2", headers=h).get_json()
    assert page["meta"]["total"] == 2 and page["meta"]["pages"] == 2 and len(page["data"]) == 1


def test_archive_hides_task(client, world):
    task_id = _new(client, world).get_json()["data"]["id"]
    assert client.post(f"/api/v1/tasks/{task_id}/archive", headers=world["h"]["m1"]).status_code == 200
    assert client.get("/api/v1/tasks", headers=world["h"]["m1"]).get_json()["meta"]["total"] == 0


def test_dashboard_stats_are_scoped_and_real(client, world):
    _new(client, world)
    _new(client, world, deadline=(date.today() - timedelta(days=1)).isoformat(), start_date=(date.today() - timedelta(days=5)).isoformat())
    client.post("/api/v1/tasks", headers=world["h"]["m2"], json=task_payload(world["p2"], world["e3"]))
    admin = client.get("/api/v1/dashboard/stats", headers=world["h"]["admin"]).get_json()["data"]
    m1 = client.get("/api/v1/dashboard/stats", headers=world["h"]["m1"]).get_json()["data"]
    e1 = client.get("/api/v1/dashboard/stats", headers=world["h"]["e1"]).get_json()["data"]
    e2 = client.get("/api/v1/dashboard/stats", headers=world["h"]["e2"]).get_json()["data"]
    assert (admin["tasks"]["total"], m1["tasks"]["total"], e1["tasks"]["total"], e2["tasks"]["total"]) == (3, 2, 2, 0)
    assert m1["tasks"]["overdue"] == 1 and m1["tasks"]["pending"] == 2 and admin["scope"] == "all"
    assert "users" in admin and "pending_reviews" in m1 and "users" not in m1


def test_csv_export_escapes_formulas_and_is_role_limited(client, world):
    _new(client, world, title="=HYPERLINK(\"http://evil\")")
    res = client.get("/api/v1/reports/export/tasks.csv", headers=world["h"]["m1"])
    assert res.status_code == 200 and res.mimetype == "text/csv"
    text = res.get_data(as_text=True)
    assert "'=HYPERLINK" in text and ",=HYPERLINK" not in text
    assert client.get("/api/v1/reports/export/tasks.csv", headers=world["h"]["e1"]).status_code == 403


def test_reports_summary_shape(client, world):
    _new(client, world)
    data = client.get("/api/v1/reports/summary", headers=world["h"]["m1"]).get_json()["data"]
    for key in ("range", "totals", "by_priority", "by_employee", "completion_trend", "rejection_trend",
                "risk_distribution", "analysis_by_severity"):
        assert key in data
    assert "by_employee" not in client.get("/api/v1/reports/summary", headers=world["h"]["e1"]).get_json()["data"]
    assert client.get("/api/v1/reports/summary?from=bad", headers=world["h"]["m1"]).status_code == 422
