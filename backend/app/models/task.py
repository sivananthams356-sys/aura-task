from app.extensions import db
from app.models.base import iso, utcnow


class Task(db.Model):
    __tablename__ = "tasks"
    __table_args__ = (
        db.CheckConstraint("progress >= 0 AND progress <= 100", name="ck_tasks_progress"),
        db.CheckConstraint("priority IN ('Low','Medium','High','Critical')", name="ck_tasks_priority"),
        db.CheckConstraint("status IN ('Pending','In Progress','Under Review','Completed','Blocked')",
                           name="ck_tasks_status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    manager_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    priority = db.Column(db.String(10), nullable=False, default="Medium")
    status = db.Column(db.String(20), nullable=False, default="Pending", index=True)
    progress = db.Column(db.Integer, nullable=False, default=0)
    start_date = db.Column(db.Date, nullable=True)
    deadline = db.Column(db.Date, nullable=False, index=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    estimated_hours = db.Column(db.Float, nullable=True)
    actual_hours = db.Column(db.Float, nullable=True)
    review_feedback = db.Column(db.Text, nullable=True)
    rejection_count = db.Column(db.Integer, nullable=False, default=0)
    reopen_count = db.Column(db.Integer, nullable=False, default=0)
    last_progress_update = db.Column(db.DateTime, nullable=True)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    project = db.relationship("Project", foreign_keys=[project_id])
    assignee = db.relationship("User", foreign_keys=[assignee_id])
    manager = db.relationship("User", foreign_keys=[manager_id])

    @property
    def is_overdue(self):
        return self.status != "Completed" and self.deadline < utcnow().date()

    def to_dict(self):
        return {
            "id": self.id, "title": self.title, "description": self.description,
            "project_id": self.project_id, "project_name": self.project.name if self.project else None,
            "assignee_id": self.assignee_id, "assignee_name": self.assignee.name if self.assignee else None,
            "manager_id": self.manager_id, "manager_name": self.manager.name if self.manager else None,
            "priority": self.priority, "status": self.status, "progress": self.progress,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "deadline": self.deadline.isoformat(), "completed_at": iso(self.completed_at),
            "estimated_hours": self.estimated_hours, "actual_hours": self.actual_hours,
            "review_feedback": self.review_feedback, "rejection_count": self.rejection_count,
            "reopen_count": self.reopen_count, "last_progress_update": iso(self.last_progress_update),
            "is_overdue": self.is_overdue, "is_archived": self.is_archived,
            "created_by": self.created_by, "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
        }


class TaskHistory(db.Model):
    __tablename__ = "task_history"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(30), nullable=False)
    field = db.Column(db.String(40), nullable=True)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    actor = db.relationship("User", foreign_keys=[actor_id])

    def to_dict(self):
        return {"id": self.id, "task_id": self.task_id, "actor_id": self.actor_id,
                "actor_name": self.actor.name if self.actor else None, "action": self.action,
                "field": self.field, "old_value": self.old_value, "new_value": self.new_value,
                "created_at": iso(self.created_at)}


class TaskComment(db.Model):
    __tablename__ = "task_comments"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    author = db.relationship("User", foreign_keys=[author_id])

    def to_dict(self):
        return {"id": self.id, "task_id": self.task_id, "author_id": self.author_id,
                "author_name": self.author.name if self.author else None, "body": self.body,
                "created_at": iso(self.created_at)}
