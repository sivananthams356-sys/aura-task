"""Data-scoping rules: who may see which rows. Every route uses these helpers."""
from app.errors import ApiError
from app.extensions import db
from app.models import CodeAnalysisReport, Task, User


def scoped_tasks(user, include_archived=False):
    q = Task.query
    if user.role == "manager":
        q = q.filter(Task.manager_id == user.id)
    elif user.role == "employee":
        q = q.filter(Task.assignee_id == user.id)
    if not include_archived:
        q = q.filter(Task.is_archived.is_(False))
    return q


def can_view_task(user, task):
    return (user.role == "admin"
            or (user.role == "manager" and task.manager_id == user.id)
            or (user.role == "employee" and task.assignee_id == user.id))


def get_task_or_404(user, task_id):
    task = db.session.get(Task, task_id)
    if task is None or not can_view_task(user, task):
        raise ApiError(404, "NOT_FOUND", "Task not found")
    return task


def can_view_user(viewer, target):
    return (viewer.role == "admin" or viewer.id == target.id
            or (viewer.role == "manager" and target.manager_id == viewer.id))


def team_user_ids(manager):
    return [u.id for u in User.query.filter_by(manager_id=manager.id).all()]


def scoped_reports(user):
    q = CodeAnalysisReport.query
    if user.role == "manager":
        q = q.filter(CodeAnalysisReport.submitted_by.in_(team_user_ids(user) + [user.id]))
    elif user.role == "employee":
        q = q.filter(CodeAnalysisReport.submitted_by == user.id)
    return q
