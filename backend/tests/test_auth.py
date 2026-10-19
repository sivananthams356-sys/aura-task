from app.extensions import db
from app.models import User
from tests.helpers import PASSWORD, login, make_user


def test_password_is_hashed(app):
    user = make_user("employee", "x@test.com")
    assert user.password_hash != PASSWORD
    assert user.check_password(PASSWORD) and not user.check_password("wrong")


def test_login_success_returns_token_and_user(client, app):
    make_user("admin", "a@test.com")
    res = client.post("/api/v1/auth/login", json={"email": "A@test.com", "password": PASSWORD})
    data = res.get_json()["data"]
    assert res.status_code == 200 and data["token_type"] == "Bearer" and data["user"]["role"] == "admin"
    assert "password_hash" not in data["user"]


def test_login_wrong_password_and_unknown_email_give_same_error(client, app):
    make_user("admin", "a@test.com")
    bad_pw = client.post("/api/v1/auth/login", json={"email": "a@test.com", "password": "nope"})
    unknown = client.post("/api/v1/auth/login", json={"email": "ghost@test.com", "password": "nope"})
    assert bad_pw.status_code == unknown.status_code == 401
    assert bad_pw.get_json() == unknown.get_json()
    assert bad_pw.get_json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_validation_error(client):
    res = client.post("/api/v1/auth/login", json={"email": "not-an-email"})
    body = res.get_json()
    assert res.status_code == 422 and body["error"]["code"] == "VALIDATION_ERROR"
    assert "email" in body["error"]["details"] and "password" in body["error"]["details"]


def test_deactivated_account_cannot_login_and_token_stops_working(client, world):
    h = world["h"]["e1"]
    assert client.get("/api/v1/auth/me", headers=h).status_code == 200
    world["e1"].is_active = False
    db.session.commit()
    assert client.get("/api/v1/auth/me", headers=h).status_code == 403
    res = client.post("/api/v1/auth/login", json={"email": "e1@test.com", "password": PASSWORD})
    assert res.status_code == 403 and res.get_json()["error"]["code"] == "ACCOUNT_DEACTIVATED"


def test_protected_endpoint_requires_token(client):
    for url in ("/api/v1/auth/me", "/api/v1/tasks", "/api/v1/users", "/api/v1/dashboard/stats"):
        res = client.get(url)
        assert res.status_code == 401 and res.get_json()["error"]["code"] == "UNAUTHORIZED"
    bad = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
    assert bad.status_code == 401


def test_logout_revokes_token(client, world):
    h = world["h"]["e1"]
    assert client.post("/api/v1/auth/logout", headers=h).status_code == 200
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401


def test_change_password(client, world):
    h = world["h"]["e1"]
    assert client.post("/api/v1/auth/change-password", headers=h,
                       json={"current_password": "wrong", "new_password": "NewPassw0rd99"}).status_code == 401
    assert client.post("/api/v1/auth/change-password", headers=h,
                       json={"current_password": PASSWORD, "new_password": "short1"}).status_code == 422
    ok = client.post("/api/v1/auth/change-password", headers=h,
                     json={"current_password": PASSWORD, "new_password": "NewPassw0rd99"})
    assert ok.status_code == 200
    login(client, "e1@test.com", "NewPassw0rd99")


def test_admin_creates_users_with_rules(client, world):
    h = world["h"]["admin"]
    good = {"name": "New Emp", "email": "new@test.com", "password": "Passw0rd-New1", "role": "employee",
            "manager_id": world["m1"].id}
    res = client.post("/api/v1/users", headers=h, json=good)
    assert res.status_code == 201 and res.get_json()["data"]["manager_id"] == world["m1"].id
    assert client.post("/api/v1/users", headers=h, json=good).status_code == 409           # duplicate email
    assert client.post("/api/v1/users", headers=h, json={**good, "email": "n2@test.com", "manager_id": None}).status_code == 422
    assert client.post("/api/v1/users", headers=h, json={**good, "email": "n3@test.com", "password": "weak"}).status_code == 422
    assert db.session.query(User).filter_by(email="n3@test.com").first() is None


def test_admin_cannot_deactivate_self(client, world):
    res = client.post(f"/api/v1/users/{world['admin'].id}/deactivate", headers=world["h"]["admin"])
    assert res.status_code == 409
