from datetime import date, timedelta

from app.extensions import db
from app.models import Project, User

PASSWORD = "Passw0rd-Test1"


def make_user(role, email, name=None, manager=None, active=True):
    user = User(name=name or email.split("@")[0].title(), email=email, role=role,
                manager_id=manager.id if manager else None, is_active=active)
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


def make_project(creator, members, name="Test Project"):
    project = Project(name=name, created_by=creator.id)
    project.members = list(members)
    db.session.add(project)
    db.session.commit()
    return project


def login(client, email, password=PASSWORD):
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.get_json()
    return {"Authorization": "Bearer " + res.get_json()["data"]["access_token"]}


def task_payload(project, assignee, **overrides):
    data = {"title": "Build feature", "description": "details", "project_id": project.id,
            "assignee_id": assignee.id, "priority": "High", "start_date": date.today().isoformat(),
            "deadline": (date.today() + timedelta(days=10)).isoformat(), "estimated_hours": 8}
    data.update(overrides)
    return data
