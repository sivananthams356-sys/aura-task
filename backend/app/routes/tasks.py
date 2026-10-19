from flask import Blueprint, request
from sqlalchemy import case
from sqlalchemy.orm import joinedload

from app.errors import json_body, ok, paginate
from app.extensions import db
from app.models import PRIORITIES, STATUSES, Task, TaskComment, TaskHistory, utcnow
from app.schemas.validators import Validator
from app.security.decorators import auth_required, current_user
from app.services import task_service as svc
from app.services.access import get_task_or_404, scoped_tasks

bp = Blueprint("tasks", __name__, url_prefix="/api/v1/tasks")
SORTS = {
    "deadline": Task.deadline, "created_at": Task.created_at, "progress": Task.progress,
    "priority": case({"Low": 1, "Medium": 2, "High": 3, "Critical": 4}, value=Task.priority),
}


def _task_dict(task):
    return ok(task.to_dict())


@bp.get("")
@auth_required()
def list_tasks():
    me = current_user()
    q = scoped_tasks(me, include_archived=request.args.get("is_archived") == "true")
    if request.args.get("status") in STATUSES:
        q = q.filter(Task.status == request.args["status"])
    if request.args.get("priority") in PRIORITIES:
        q = q.filter(Task.priority == request.args["priority"])
    if request.args.get("project_id", type=int):
        q = q.filter(Task.project_id == request.args.get("project_id", type=int))
    if request.args.get("assignee_id", type=int) and me.role != "employee":
        q = q.filter(Task.assignee_id == request.args.get("assignee_id", type=int))
    if request.args.get("overdue") == "true":
        q = q.filter(Task.deadline < utcnow().date(), Task.status != "Completed")
    text = (request.args.get("q") or "").strip()[:100]
    if text:
        q = q.filter(Task.title.ilike(f"%{text}%"))
    sort = request.args.get("sort", "deadline")
    column = SORTS.get(sort.lstrip("-"), Task.deadline)
    q = q.order_by(column.desc() if sort.startswith("-") else column.asc(), Task.id)
    q = q.options(joinedload(Task.assignee), joinedload(Task.manager), joinedload(Task.project))
    return paginate(q, lambda t: t.to_dict())


@bp.post("")
@auth_required("admin", "manager")
def create_task():
    v = Validator(json_body())
    data = {"title": v.string("title", 3, 150), "description": v.string("description", 0, 5000, required=False),
            "project_id": v.integer("project_id", 1), "assignee_id": v.integer("assignee_id", 1),
            "priority": v.enum("priority", PRIORITIES), "start_date": v.date("start_date", required=False),
            "deadline": v.date("deadline"), "estimated_hours": v.number("estimated_hours", 0.1, 500)}
    v.done()
    return ok(svc.create_task(current_user(), data).to_dict(), 201)


@bp.get("/<int:task_id>")
@auth_required()
def get_task(task_id):
    return _task_dict(get_task_or_404(current_user(), task_id))


@bp.patch("/<int:task_id>")
@auth_required("admin", "manager")
def update_task(task_id):
    task = get_task_or_404(current_user(), task_id)
    v = Validator(json_body())
    data = {}
    for key, value in (("title", v.string("title", 3, 150, False)),
                       ("description", v.string("description", 0, 5000, False)),
                       ("priority", v.enum("priority", PRIORITIES, False)),
                       ("start_date", v.date("start_date", False)), ("deadline", v.date("deadline", False)),
                       ("estimated_hours", v.number("estimated_hours", 0.1, 500, False)),
                       ("assignee_id", v.integer("assignee_id", 1, required=False))):
        if value is not None:
            data[key] = value
    v.done()
    return _task_dict(svc.update_task(current_user(), task, data))


@bp.post("/<int:task_id>/archive")
@auth_required("admin", "manager")
def archive_task(task_id):
    task = get_task_or_404(current_user(), task_id)
    return _task_dict(svc.archive_task(current_user(), task))


@bp.post("/<int:task_id>/progress")
@auth_required("employee")
def update_progress(task_id):
    task = get_task_or_404(current_user(), task_id)
    v = Validator(json_body())
    progress = v.integer("progress", 0, 100)
    hours = v.number("actual_hours", 0, 10000, required=False)
    note = v.string("note", 1, 1000, required=False)
    v.done()
    return _task_dict(svc.update_progress(current_user(), task, progress, hours, note))


@bp.post("/<int:task_id>/status")
@auth_required("admin", "manager", "employee")
def change_status(task_id):
    task = get_task_or_404(current_user(), task_id)
    v = Validator(json_body())
    status, reason = v.enum("status", STATUSES), v.string("reason", 1, 500, required=False)
    v.done()
    return _task_dict(svc.change_status(current_user(), task, status, reason))


@bp.post("/<int:task_id>/submit")
@auth_required("employee")
def submit(task_id):
    task = get_task_or_404(current_user(), task_id)
    v = Validator(request.get_json(silent=True) or {})
    note = v.string("note", 1, 1000, required=False)
    v.done()
    return _task_dict(svc.submit_for_review(current_user(), task, note))


@bp.post("/<int:task_id>/review")
@auth_required("manager")
def review(task_id):
    task = get_task_or_404(current_user(), task_id)
    v = Validator(json_body())
    decision = v.enum("decision", ("approve", "reject"))
    feedback = v.string("feedback", 3, 1000, required=False)
    v.done()
    return _task_dict(svc.review_task(current_user(), task, decision, feedback))


@bp.post("/<int:task_id>/reopen")
@auth_required("admin", "manager")
def reopen(task_id):
    task = get_task_or_404(current_user(), task_id)
    v = Validator(json_body())
    reason = v.string("reason", 3, 1000)
    v.done()
    return _task_dict(svc.reopen_task(current_user(), task, reason))


@bp.get("/<int:task_id>/history")
@auth_required()
def history(task_id):
    task = get_task_or_404(current_user(), task_id)
    q = TaskHistory.query.filter_by(task_id=task.id).order_by(TaskHistory.id.desc())
    return paginate(q, lambda h: h.to_dict())


@bp.get("/<int:task_id>/comments")
@auth_required()
def list_comments(task_id):
    task = get_task_or_404(current_user(), task_id)
    comments = TaskComment.query.filter_by(task_id=task.id).order_by(TaskComment.id).all()
    return ok([c.to_dict() for c in comments])


@bp.post("/<int:task_id>/comments")
@auth_required()
def add_comment(task_id):
    task = get_task_or_404(current_user(), task_id)
    v = Validator(json_body())
    body = v.string("body", 1, 1000)
    v.done()
    comment = TaskComment(task_id=task.id, author_id=current_user().id, body=body)
    db.session.add(comment)
    db.session.commit()
    return ok(comment.to_dict(), 201)
