import os

from tests.helpers import task_payload

GOOD = "import os\n\ndef add(a, b):\n    return a + b\n"


def _analyze(client, headers, code=GOOD, **extra):
    return client.post("/api/v1/analysis/python", headers=headers, json={"code": code, "filename": "a.py", **extra})


def test_analysis_returns_structured_findings(client, world):
    res = _analyze(client, world["h"]["e1"], "import os\ntry:\n    x = 1\nexcept:\n    pass\neval('1')\n")
    data = res.get_json()["data"]
    assert res.status_code == 201 and data["syntax_valid"] is True
    assert data["summary"]["total"] == len(data["findings"]) and data["disclaimer"]
    for f in data["findings"]:
        for key in ("rule_id", "severity", "category", "line", "message", "explanation", "suggestion", "tool"):
            assert key in f
    assert any(f["severity"] == "high" for f in data["findings"])       # eval()
    assert "tools_used" in data and "code" in data


def test_syntax_error_is_reported_not_crashed(client, world):
    data = _analyze(client, world["h"]["e1"], "def broken(:\n    pass").get_json()["data"]
    assert data["syntax_valid"] is False and data["findings"][0]["rule_id"] == "SYNTAX"
    assert data["findings"][0]["severity"] == "critical"


def test_malformed_and_oversized_input(client, world):
    h = world["h"]["e1"]
    assert _analyze(client, h, "").status_code == 422
    assert _analyze(client, h, 12345).status_code == 422
    assert _analyze(client, h, "x = 1\x00").status_code == 422
    assert _analyze(client, h, "x = 1\n" * 60000).status_code == 413          # > 50 KB
    assert _analyze(client, h, "x = 1\n" * 2500).status_code == 413           # > 2000 lines
    assert _analyze(client, h, GOOD, filename="../../etc/passwd").status_code == 422
    assert client.post("/api/v1/analysis/python", headers=h, data="not json").status_code == 400
    deep = _analyze(client, h, "(" * 5000)
    assert deep.status_code == 201 and deep.get_json()["data"]["syntax_valid"] is False


def test_submitted_code_is_never_executed(client, world, tmp_path):
    marker = tmp_path / "marker.txt"
    code = f"open({str(marker)!r}, 'w').write('executed')\nraise SystemExit(1)\n"
    assert _analyze(client, world["h"]["e1"], code).status_code == 201
    assert not marker.exists()


def test_errors_do_not_leak_paths_or_traces(client, world):
    res = _analyze(client, world["h"]["e1"], "def x(:")
    text = res.get_data(as_text=True)
    assert "Traceback" not in text and os.getcwd() not in text and "site-packages" not in text


def test_report_access_is_scoped(client, world):
    report_id = _analyze(client, world["h"]["e1"]).get_json()["data"]["id"]
    url = f"/api/v1/analysis/reports/{report_id}"
    assert client.get(url, headers=world["h"]["e1"]).status_code == 200      # owner
    assert client.get(url, headers=world["h"]["m1"]).status_code == 200      # their manager
    assert client.get(url, headers=world["h"]["admin"]).status_code == 200
    assert client.get(url, headers=world["h"]["e2"]).status_code == 404      # teammate
    assert client.get(url, headers=world["h"]["m2"]).status_code == 404      # other manager
    assert client.get(url, headers=world["h"]["e3"]).status_code == 404
    mine = client.get("/api/v1/analysis/reports", headers=world["h"]["e2"]).get_json()
    assert mine["meta"]["total"] == 0
    filtered = client.get(url + "?severity=critical", headers=world["h"]["e1"]).get_json()["data"]
    assert all(f["severity"] == "critical" for f in filtered["findings"])


def test_analysis_can_link_to_visible_task_only(client, world):
    task = client.post("/api/v1/tasks", headers=world["h"]["m1"], json=task_payload(world["p1"], world["e1"]))
    task_id = task.get_json()["data"]["id"]
    assert _analyze(client, world["h"]["e1"], task_id=task_id).status_code == 201
    assert _analyze(client, world["h"]["e2"], task_id=task_id).status_code == 404
