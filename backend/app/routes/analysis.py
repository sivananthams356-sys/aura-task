from flask import Blueprint, current_app, request

from app.analysis.runner import analyze_python
from app.errors import ApiError, json_body, ok, paginate
from app.extensions import db
from app.models import SEVERITIES, CodeAnalysisFinding, CodeAnalysisReport
from app.schemas.validators import Validator
from app.security.decorators import auth_required, current_user
from app.services.access import get_task_or_404, scoped_reports

bp = Blueprint("analysis", __name__, url_prefix="/api/v1/analysis")


@bp.post("/python")
@auth_required()
def analyze():
    """Static analysis only. The submitted code is parsed, NEVER executed."""
    body = json_body()
    code = body.get("code")
    if not isinstance(code, str) or not code.strip():
        raise ApiError(422, "VALIDATION_ERROR", "Validation failed", {"code": "Must be non-empty text"})
    if len(code.encode("utf-8")) > current_app.config["MAX_CODE_BYTES"] \
            or code.count("\n") + 1 > current_app.config["MAX_CODE_LINES"]:
        raise ApiError(413, "PAYLOAD_TOO_LARGE", "Code is too large ("
                       f"max {current_app.config['MAX_CODE_BYTES']} bytes / {current_app.config['MAX_CODE_LINES']} lines)")
    if "\x00" in code:
        raise ApiError(422, "VALIDATION_ERROR", "Validation failed", {"code": "Must not contain null characters"})
    v = Validator(body)
    filename = v.string("filename", 1, 100, required=False) or "snippet.py"
    task_id = v.integer("task_id", 1, required=False)
    v.done()
    import re
    if not re.fullmatch(r"[A-Za-z0-9._-]+", filename):
        raise ApiError(422, "VALIDATION_ERROR", "Validation failed",
                       {"filename": "Use only letters, digits, '.', '_' and '-'"})
    me = current_user()
    if task_id:
        get_task_or_404(me, task_id)

    result = analyze_python(code)
    findings = result["findings"]
    counts = {s: sum(f["severity"] == s for f in findings) for s in SEVERITIES}
    report = CodeAnalysisReport(
        submitted_by=me.id, task_id=task_id, filename=filename, line_count=code.count("\n") + 1, code=code,
        syntax_valid=result["syntax_valid"], tools_used=",".join(result["tools_used"]),
        notes="\n".join(result["notes"]), count_total=len(findings), count_critical=counts["critical"],
        count_high=counts["high"], count_medium=counts["medium"], count_low=counts["low"], count_info=counts["info"])
    report.findings = [CodeAnalysisFinding(**f) for f in findings]
    db.session.add(report)
    db.session.commit()
    return ok(report.to_dict(detail=True), 201)


@bp.get("/reports")
@auth_required()
def list_reports():
    me = current_user()
    q = scoped_reports(me)
    if request.args.get("submitted_by", type=int) and me.role != "employee":
        q = q.filter(CodeAnalysisReport.submitted_by == request.args.get("submitted_by", type=int))
    return paginate(q.order_by(CodeAnalysisReport.id.desc()), lambda r: r.to_dict())


@bp.get("/reports/<int:report_id>")
@auth_required()
def get_report(report_id):
    report = scoped_reports(current_user()).filter(CodeAnalysisReport.id == report_id).first()
    if report is None:
        raise ApiError(404, "NOT_FOUND", "Report not found")
    severity = request.args.get("severity")
    return ok(report.to_dict(detail=True, severity=severity if severity in SEVERITIES else None))
