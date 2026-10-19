from tests.helpers import task_payload


def _make_task(client, world, assignee="e1", manager="m1", project="p1"):
    res = client.post("/api/v1/tasks", headers=world["h"][manager], json=task_payload(world[project], world[assignee]))
    assert res.status_code == 201, res.get_json()
    return res.get_json()["data"]["id"]


def test_employee_cannot_manage_users_or_create_tasks(client, world):
    h = world["h"]["e1"]
    assert client.get("/api/v1/users", headers=h).status_code == 403
    assert client.post("/api/v1/users", headers=h, json={}).status_code == 403
    assert client.post("/api/v1/tasks", headers=h, json=task_payload(world["p1"], world["e1"])).status_code == 403
    assert client.get("/api/v1/predictions", headers=h).status_code == 403
    assert client.get("/api/v1/reports/export/tasks.csv", headers=h).status_code == 403


def test_manager_cannot_manage_users_or_projects(client, world):
    h = world["h"]["m1"]
    assert client.post("/api/v1/users", headers=h, json={}).status_code == 403
    assert client.post("/api/v1/projects", headers=h, json={"name": "X project"}).status_code == 403
    assert client.post(f"/api/v1/users/{world['e1'].id}/deactivate", headers=h).status_code == 403


def test_manager_lists_only_own_team(client, world):
    res = client.get("/api/v1/users", headers=world["h"]["m1"])
    emails = {u["email"] for u in res.get_json()["data"]}
    assert emails == {"e1@test.com", "e2@test.com"}
    assert client.get(f"/api/v1/users/{world['e3'].id}", headers=world["h"]["m1"]).status_code == 404


def test_employee_sees_only_own_tasks(client, world):
    mine = _make_task(client, world, "e1")
    other = _make_task(client, world, "e2")
    listed = client.get("/api/v1/tasks", headers=world["h"]["e1"]).get_json()["data"]
    assert [t["id"] for t in listed] == [mine]
    assert client.get(f"/api/v1/tasks/{other}", headers=world["h"]["e1"]).status_code == 404
    assert client.get(f"/api/v1/tasks/{other}/history", headers=world["h"]["e1"]).status_code == 404
    assert client.post(f"/api/v1/tasks/{other}/comments", headers=world["h"]["e1"], json={"body": "hi"}).status_code == 404


def test_other_manager_cannot_see_or_change_task(client, world):
    task_id = _make_task(client, world, "e1")
    h = world["h"]["m2"]
    assert client.get(f"/api/v1/tasks/{task_id}", headers=h).status_code == 404
    assert client.patch(f"/api/v1/tasks/{task_id}", headers=h, json={"title": "hijack"}).status_code == 404
    assert client.get(f"/api/v1/predictions/tasks/{task_id}", headers=h).status_code == 404


def test_manager_cannot_assign_outside_team(client, world):
    res = client.post("/api/v1/tasks", headers=world["h"]["m1"], json=task_payload(world["p1"], world["e3"]))
    assert res.status_code in (403, 422)


def test_employee_cannot_update_someone_elses_progress(client, world):
    task_id = _make_task(client, world, "e1")
    client.post(f"/api/v1/tasks/{task_id}/status", headers=world["h"]["e1"], json={"status": "In Progress"})
    assert client.post(f"/api/v1/tasks/{task_id}/progress", headers=world["h"]["e2"], json={"progress": 10}).status_code == 404
    assert client.post(f"/api/v1/tasks/{task_id}/progress", headers=world["h"]["m1"], json={"progress": 10}).status_code == 403


def test_only_the_tasks_manager_can_review(client, world):
    task_id = _make_task(client, world, "e1")
    e1, m1 = world["h"]["e1"], world["h"]["m1"]
    client.post(f"/api/v1/tasks/{task_id}/status", headers=e1, json={"status": "In Progress"})
    client.post(f"/api/v1/tasks/{task_id}/progress", headers=e1, json={"progress": 95})
    assert client.post(f"/api/v1/tasks/{task_id}/submit", headers=e1, json={}).status_code == 200
    body = {"decision": "approve", "feedback": "ok"}
    assert client.post(f"/api/v1/tasks/{task_id}/review", headers=e1, json=body).status_code == 403
    assert client.post(f"/api/v1/tasks/{task_id}/review", headers=world["h"]["admin"], json=body).status_code == 403
    assert client.post(f"/api/v1/tasks/{task_id}/review", headers=world["h"]["m2"], json=body).status_code == 404
    assert client.post(f"/api/v1/tasks/{task_id}/review", headers=m1, json=body).status_code == 200


def test_admin_sees_everything(client, world):
    _make_task(client, world, "e1")
    _make_task(client, world, "e3", "m2", "p2")
    res = client.get("/api/v1/tasks", headers=world["h"]["admin"])
    assert res.get_json()["meta"]["total"] == 2
