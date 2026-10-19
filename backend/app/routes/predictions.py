from flask import Blueprint, request

from app.ai import predict as ai
from app.errors import json_body, ok, paginate_list
from app.models import OPEN_STATUSES, Task
from app.schemas.validators import Validator
from app.security.decorators import auth_required, current_user
from app.services import prediction_service as svc
from app.services.access import get_task_or_404, scoped_tasks

bp = Blueprint("predictions", __name__, url_prefix="/api/v1/predictions")


@bp.get("/model-info")
@auth_required("admin", "manager")
def model_info():
    return ok(ai.model_info())


@bp.get("/tasks/<int:task_id>")
@auth_required()
def task_prediction(task_id):
    task = get_task_or_404(current_user(), task_id)
    return ok(svc.get_prediction(task).to_dict())


@bp.post("/run")
@auth_required("admin", "manager")
def run():
    v = Validator(request.get_json(silent=True) or {})
    ids = v.id_list("task_ids")
    v.done()
    q = scoped_tasks(current_user()).filter(Task.status.in_(OPEN_STATUSES))
    if ids:
        q = q.filter(Task.id.in_(ids))
    records = [svc.compute_and_store(t) for t in q.limit(500).all()]
    return ok({"scored": len(records), "predictions": [r.to_dict() for r in records]})


@bp.get("")
@auth_required("admin", "manager")
def list_predictions():
    q = scoped_tasks(current_user()).filter(Task.status.in_(OPEN_STATUSES))
    if request.args.get("project_id", type=int):
        q = q.filter(Task.project_id == request.args.get("project_id", type=int))
    tasks = {t.id: t for t in q.all()}
    items = []
    for task_id, rec in svc.latest_for_tasks(list(tasks)).items():
        if request.args.get("risk_category") in (None, "", rec.risk_category):
            t = tasks[task_id]
            items.append({**rec.to_dict(), "title": t.title, "assignee_name": t.assignee.name,
                          "deadline": t.deadline.isoformat()})
    items.sort(key=lambda i: (-(i["risk_score"] if i["risk_score"] is not None else -1),
                              {"High": 0, "Medium": 1, "Low": 2}[i["risk_category"]]))
    return paginate_list(items)
