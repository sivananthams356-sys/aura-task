import pytest

from app import create_app
from app.extensions import db
from config import TestingConfig
from tests.helpers import login, make_project, make_user


@pytest.fixture()
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def world(app, client):
    """Two teams: admin; manager1 (+emp1, emp2); manager2 (+emp3). One shared project for team 1."""
    admin = make_user("admin", "admin@test.com")
    m1 = make_user("manager", "m1@test.com")
    m2 = make_user("manager", "m2@test.com")
    e1 = make_user("employee", "e1@test.com", manager=m1)
    e2 = make_user("employee", "e2@test.com", manager=m1)
    e3 = make_user("employee", "e3@test.com", manager=m2)
    p1 = make_project(admin, [m1, e1, e2], "Team One Project")
    p2 = make_project(admin, [m2, e3], "Team Two Project")
    tokens = {name: login(client, u.email) for name, u in
              {"admin": admin, "m1": m1, "m2": m2, "e1": e1, "e2": e2, "e3": e3}.items()}
    return {"admin": admin, "m1": m1, "m2": m2, "e1": e1, "e2": e2, "e3": e3, "p1": p1, "p2": p2, "h": tokens}
