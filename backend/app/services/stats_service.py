"""Dashboard + report numbers, always calculated from the caller's authorised data."""
from collections import Counter
from datetime import datetime, time, timedelta

from sqlalchemy import func

from app.extensions import db
from app.models import (CodeAnalysisFinding, CodeAnalysisReport, OPEN_STATUSES, Task, TaskHistory, User, utcnow)
from app.services.access import scoped_reports, scoped_tasks
from app.services.prediction_service import latest_for_tasks

STATUS_KEYS = {"Pending": "pending", "In Progress": "in_progress", "Under Review": "under_review",
               "Completed": "completed", "Blocked": "blocked"}


def task_totals(q):
    counts = dict(q.with_entities(Task.status, func.count(Task.id)).group_by(Task.status).all())
    totals = {key: counts.get(status, 0) for status, key in STATUS_KEYS.items()}
    totals["total"] = sum(totals.values())
    totals["overdue"] = q.filter(Task.deadline < utcnow().date(), Task.status != "Completed").count()
    return {"total": totals.pop("total"), **totals, "overdue": totals["overdue"]}


def by_priority(q):
    counts = dict(q.with_entities(Task.priority, func.count(Task.id)).group_by(Task.priority).all())
    return {p: counts.get(p, 0) for p in ("Low", "Medium", "High", "Critical")}


def risk_distribution(q):
    ids = [i for (i,) in q.filter(Task.status.in_(OPEN_STATUSES)).with_entities(Task.id).all()]
    latest = latest_for_tasks(ids)
    dist = {"Low": 0, "Medium": 0, "High": 0}
    for rec in latest.values():
        dist[rec.risk_category] += 1
    dist["unscored"] = len(ids) - len(latest)
    return dist


def analysis_by_severity(user):
    ids = [i for (i,) in scoped_reports(user).with_entities(CodeAnalysisReport.id).all()]
    result = {s: 0 for s in ("critical", "high", "medium", "low", "info")}
    if ids:
        rows = (db.session.query(CodeAnalysisFinding.severity, func.count(CodeAnalysisFinding.id))
                .filter(CodeAnalysisFinding.report_id.in_(ids)).group_by(CodeAnalysisFinding.severity).all())
        result.update(dict(rows))
    return result


def dashboard(user):
    q = scoped_tasks(user)
    today = utcnow().date()
    upcoming = (q.filter(Task.status != "Completed", Task.deadline >= today)
                .order_by(Task.deadline).limit(5).all())
    data = {"scope": {"admin": "all", "manager": "team", "employee": "own"}[user.role],
            "tasks": task_totals(q), "by_priority": by_priority(q), "risk_distribution": risk_distribution(q),
            "upcoming_deadlines": [{"task_id": t.id, "title": t.title, "deadline": t.deadline.isoformat(),
                                    "assignee_name": t.assignee.name} for t in upcoming]}
    if user.role == "manager":
        data["pending_reviews"] = q.filter(Task.status == "Under Review").count()
    if user.role == "admin":
        data["users"] = {"total": User.query.count(), "active": User.query.filter_by(is_active=True).count()}
    return data


def report_summary(user, date_from, date_to):
    q = scoped_tasks(user)
    start = datetime.combine(date_from, time.min)
    end = datetime.combine(date_to + timedelta(days=1), time.min)
    completed = Counter(
        t.completed_at.date().isoformat() for t in
        q.filter(Task.completed_at >= start, Task.completed_at < end).all())
    ids = [i for (i,) in q.with_entities(Task.id).all()]
    trend = {}
    if ids:
        events = TaskHistory.query.filter(TaskHistory.task_id.in_(ids), TaskHistory.action.in_(("rejected", "reopened")),
                                          TaskHistory.created_at >= start, TaskHistory.created_at < end).all()
        for e in events:
            day = trend.setdefault(e.created_at.date().isoformat(), {"rejections": 0, "reopenings": 0})
            day["rejections" if e.action == "rejected" else "reopenings"] += 1
    data = {"range": {"from": date_from.isoformat(), "to": date_to.isoformat()},
            "totals": task_totals(q), "by_priority": by_priority(q),
            "completion_trend": [{"date": d, "completed": n} for d, n in sorted(completed.items())],
            "rejection_trend": [{"date": d, **v} for d, v in sorted(trend.items())],
            "risk_distribution": risk_distribution(q), "analysis_by_severity": analysis_by_severity(user)}
    if user.role != "employee":
        per = {}
        for t in q.all():
            row = per.setdefault(t.assignee_id, {"user_id": t.assignee_id, "name": t.assignee.name,
                                                 "total": 0, "completed": 0, "overdue": 0})
            row["total"] += 1
            row["completed"] += t.status == "Completed"
            row["overdue"] += t.is_overdue
        data["by_employee"] = sorted(per.values(), key=lambda r: r["name"])
    return data
