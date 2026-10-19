from app.extensions import db
from app.models.base import iso, utcnow


class CodeAnalysisReport(db.Model):
    __tablename__ = "code_analysis_reports"
    id = db.Column(db.Integer, primary_key=True)
    submitted_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True)
    filename = db.Column(db.String(100), nullable=False, default="snippet.py")
    language = db.Column(db.String(20), nullable=False, default="python")
    line_count = db.Column(db.Integer, nullable=False, default=0)
    code = db.Column(db.Text, nullable=False)  # size-limited by the API (default 50 KB)
    syntax_valid = db.Column(db.Boolean, nullable=False, default=True)
    tools_used = db.Column(db.String(100), nullable=False, default="ast")
    notes = db.Column(db.Text, nullable=True)
    count_total = db.Column(db.Integer, nullable=False, default=0)
    count_critical = db.Column(db.Integer, nullable=False, default=0)
    count_high = db.Column(db.Integer, nullable=False, default=0)
    count_medium = db.Column(db.Integer, nullable=False, default=0)
    count_low = db.Column(db.Integer, nullable=False, default=0)
    count_info = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    submitter = db.relationship("User", foreign_keys=[submitted_by])
    findings = db.relationship("CodeAnalysisFinding", backref="report", cascade="all, delete-orphan",
                               order_by="CodeAnalysisFinding.line")

    def summary(self):
        return {"total": self.count_total, "critical": self.count_critical, "high": self.count_high,
                "medium": self.count_medium, "low": self.count_low, "info": self.count_info}

    def to_dict(self, detail=False, severity=None):
        data = {"id": self.id, "filename": self.filename, "language": self.language,
                "line_count": self.line_count, "submitted_by": self.submitted_by,
                "submitted_by_name": self.submitter.name if self.submitter else None,
                "created_at": iso(self.created_at), "summary": self.summary()}
        if detail:
            data.update({
                "syntax_valid": self.syntax_valid, "code": self.code,
                "tools_used": [t for t in self.tools_used.split(",") if t],
                "notes": [n for n in (self.notes or "").split("\n") if n],
                "findings": [f.to_dict() for f in self.findings if severity in (None, f.severity)],
                "disclaimer": "Static analysis cannot detect every logical bug. "
                              "These results are rule-based, not ML predictions.",
            })
        return data


class CodeAnalysisFinding(db.Model):
    __tablename__ = "code_analysis_findings"
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("code_analysis_reports.id"), nullable=False, index=True)
    rule_id = db.Column(db.String(30), nullable=False)
    severity = db.Column(db.String(10), nullable=False, index=True)
    category = db.Column(db.String(30), nullable=False)
    line = db.Column(db.Integer, nullable=True)
    message = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    suggestion = db.Column(db.Text, nullable=False)
    tool = db.Column(db.String(20), nullable=False)

    def to_dict(self):
        return {"id": self.id, "rule_id": self.rule_id, "severity": self.severity,
                "category": self.category, "line": self.line, "message": self.message,
                "explanation": self.explanation, "suggestion": self.suggestion, "tool": self.tool}
