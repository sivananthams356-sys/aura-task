from app.extensions import db
from app.models.base import iso, utcnow

DISCLAIMERS = {
    "ml_model": "Trained on synthetic demo data. Not evidence of real-world accuracy.",
    "rule_based": "Rule-based estimate, not a trained ML prediction.",
}


class PredictionRecord(db.Model):
    __tablename__ = "prediction_records"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False, index=True)
    risk_category = db.Column(db.String(10), nullable=False)
    risk_score = db.Column(db.Float, nullable=True)
    method = db.Column(db.String(20), nullable=False)
    model_version = db.Column(db.String(60), nullable=True)
    factors = db.Column(db.JSON, nullable=False, default=list)
    suggested_actions = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    task = db.relationship("Task", foreign_keys=[task_id])

    def to_dict(self):
        return {"task_id": self.task_id, "risk_category": self.risk_category,
                "risk_score": self.risk_score, "method": self.method,
                "model_version": self.model_version, "factors": self.factors or [],
                "suggested_actions": self.suggested_actions or [],
                "predicted_at": iso(self.created_at), "disclaimer": DISCLAIMERS.get(self.method, "")}
