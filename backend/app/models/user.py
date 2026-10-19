from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.base import iso, utcnow

project_members = db.Table(
    "project_members",
    db.Column("project_id", db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (db.CheckConstraint("role IN ('admin','manager','employee')", name="ck_users_role"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email, "role": self.role,
                "manager_id": self.manager_id, "is_active": self.is_active,
                "created_at": iso(self.created_at)}


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    members = db.relationship("User", secondary=project_members, backref="projects")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description,
                "is_archived": self.is_archived, "created_by": self.created_by,
                "member_ids": sorted(m.id for m in self.members), "created_at": iso(self.created_at)}


class TokenBlocklist(db.Model):
    """Revoked JWTs (logout)."""
    __tablename__ = "token_blocklist"
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(64), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
