import csv
import io
from datetime import timedelta

from flask import Blueprint, Response, request
from sqlalchemy.orm import joinedload

from app.errors import ApiError, ok
from app.models import CodeAnalysisReport, Task, utcnow
from app.security.decorators import auth_required, current_user
from app.services import stats_service
from app.services.access import scoped_reports, scoped_tasks

bp = Blueprint("reports", __name__, url_prefix="/api/v1/reports")


def _safe(value):
    """Prevent spreadsheet formula injection in CSV cells."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def _csv_response(filename, header, rows):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(header)
    for row in rows:
        writer.writerow([_safe(c) for c in row])
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


def _parse_date(name, default):
    raw = request.args.get(name)
    if not raw:
        return default
    try:
        from datetime import date
        return date.fromisoformat(raw)
    except ValueError:
        raise ApiError(422, "VALIDATION_ERROR", "Validation failed", {name: "Must be a date in YYYY-MM-DD format"})


@bp.get("/summary")
@auth_required()
def summary():
    today = utcnow().date()
    start, end = _parse_date("from", today - timedelta(days=30)), _parse_date("to", today)
    if start > end:
        raise ApiError(422, "VALIDATION_ERROR", "Validation failed", {"from": "Must not be after 'to'"})
    return ok(stats_service.report_summary(current_user(), start, end))


@bp.get("/export/tasks.csv")
@auth_required("admin", "manager")
def export_tasks():
    q = scoped_tasks(current_user()).options(joinedload(Task.assignee), joinedload(Task.manager),
                                             joinedload(Task.project)).order_by(Task.id)
    rows = [(t.id, t.title, t.project.name, t.assignee.name, t.manager.name, t.priority, t.status, t.progress,
             t.deadline.isoformat(), t.is_overdue, t.rejection_count, t.reopen_count) for t in q.all()]
    return _csv_response("tasks.csv", ["id", "title", "project", "assignee", "manager", "priority", "status",
                                       "progress", "deadline", "is_overdue", "rejection_count", "reopen_count"], rows)


@bp.get("/export/analysis.csv")
@auth_required("admin", "manager")
def export_analysis():
    rows = []
    for report in scoped_reports(current_user()).order_by(CodeAnalysisReport.id).all():
        for f in report.findings:
            rows.append((report.id, report.filename, report.submitter.name, report.created_at.isoformat(),
                         f.rule_id, f.severity, f.category, f.line, f.tool))
    return _csv_response("analysis.csv", ["report_id", "filename", "submitted_by", "created_at", "rule_id",
                                          "severity", "category", "line", "tool"], rows)
