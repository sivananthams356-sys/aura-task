from tests.helpers import task_payload


def _task(client, world):
    return client.post("/api/v1/tasks", headers=world["h"]["m1"],
                       json=task_payload(world["p1"], world["e1"])).get_json()["data"]["id"]


def test_prediction_endpoint_shape_and_honest_labels(client, world):
    task_id = _task(client, world)
    data = client.get(f"/api/v1/predictions/tasks/{task_id}", headers=world["h"]["e1"]).get_json()["data"]
    assert data["task_id"] == task_id and data["risk_category"] in ("Low", "Medium", "High")
    assert data["method"] in ("ml_model", "rule_based") and data["predicted_at"] and data["suggested_actions"]
    if data["method"] == "rule_based":
        assert data["risk_score"] is None and "not a trained ML prediction" in data["disclaimer"]
    else:
        assert "synthetic" in data["disclaimer"].lower() and 0 <= data["risk_score"] <= 1


def test_run_and_list_predictions(client, world):
    _task(client, world)
    run = client.post("/api/v1/predictions/run", headers=world["h"]["m1"], json={}).get_json()["data"]
    assert run["scored"] == 1
    listed = client.get("/api/v1/predictions", headers=world["h"]["m1"]).get_json()
    assert listed["meta"]["total"] == 1 and "title" in listed["data"][0]
    assert client.get("/api/v1/predictions", headers=world["h"]["m2"]).get_json()["meta"]["total"] == 0
    info = client.get("/api/v1/predictions/model-info", headers=world["h"]["m1"]).get_json()["data"]
    assert "model_available" in info


def test_completed_task_is_not_predictable(client, world):
    task_id = _task(client, world)
    e1, m1 = world["h"]["e1"], world["h"]["m1"]
    client.post(f"/api/v1/tasks/{task_id}/status", headers=e1, json={"status": "In Progress"})
    client.post(f"/api/v1/tasks/{task_id}/progress", headers=e1, json={"progress": 95})
    client.post(f"/api/v1/tasks/{task_id}/submit", headers=e1, json={})
    client.post(f"/api/v1/tasks/{task_id}/review", headers=m1, json={"decision": "approve"})
    res = client.get(f"/api/v1/predictions/tasks/{task_id}", headers=e1)
    assert res.status_code == 409 and res.get_json()["error"]["code"] == "NOT_PREDICTABLE"


def test_error_format_is_consistent(client, world):
    for res in (client.get("/api/v1/nope"), client.get("/api/v1/tasks"),
                client.get("/api/v1/tasks/999999", headers=world["h"]["e1"]),
                client.post("/api/v1/tasks", headers=world["h"]["m1"], json={})):
        body = res.get_json()
        assert set(body) == {"error"} and {"code", "message"} <= set(body["error"])
