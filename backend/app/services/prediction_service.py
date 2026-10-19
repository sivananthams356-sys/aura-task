"""Glue between tasks (database) and the AI module (pure Python)."""
from sqlalchemy import func

from app.ai import predict as ai
from app.ai.features import task_to_features
from app.errors import ApiError
from app.extensions import db
from app.models import OPEN_STATUSES, PredictionRecord, Task


def open_task_count(user_id):
    return Task.query.filter(Task.assignee_id == user_id, Task.is_archived.is_(False),
                             Task.status.in_(OPEN_STATUSES)).count()


def compute_and_store(task):
    if task.is_archived or task.status == "Completed":
        raise ApiError(409, "NOT_PREDICTABLE", "Predictions are only available for open tasks")
    result = ai.predict(task_to_features(task, open_task_count(task.assignee_id)))
    rec = PredictionRecord(task_id=task.id, risk_category=result["risk_category"], risk_score=result["risk_score"],
                           method=result["method"], model_version=result["model_version"],
                           factors=result["factors"], suggested_actions=result["suggested_actions"])
    db.session.add(rec)
    db.session.commit()
    return rec


def latest_for_task(task):
    return PredictionRecord.query.filter_by(task_id=task.id).order_by(PredictionRecord.id.desc()).first()


def get_prediction(task):
    """Return the stored prediction unless the task changed since it was made."""
    rec = latest_for_task(task)
    if rec is None or rec.created_at < task.updated_at:
        rec = compute_and_store(task)
    return rec


def latest_for_tasks(task_ids):
    if not task_ids:
        return {}
    newest = (db.session.query(func.max(PredictionRecord.id))
              .filter(PredictionRecord.task_id.in_(task_ids)).group_by(PredictionRecord.task_id))
    return {r.task_id: r for r in PredictionRecord.query.filter(PredictionRecord.id.in_(newest)).all()}
