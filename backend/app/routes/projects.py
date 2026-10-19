from flask import Blueprint, request

from app.errors import ApiError, json_body, ok, paginate
from app.extensions import db
from app.models import Project, User
from app.schemas.validators import Validator
from app.security.decorators import auth_required, current_user

bp = Blueprint("projects", __name__, url_prefix="/api/v1/projects")


def _visible_or_404(project_id):
    project = db.session.get(Project, project_id)
    me = current_user()
    if project is None or (me.role != "admin" and me not in project.members):
        raise ApiError(404, "NOT_FOUND", "Project not found")
    return project


def _members(v, ids):
    if ids is None:
        return None
    users = User.query.filter(User.id.in_(ids), User.is_active.is_(True)).all()
    if len(users) != len(ids):
        v.fail("member_ids", "Every member must be an existing, active user")
        v.done()
    return users


@bp.get("")
@auth_required()
def list_projects():
    me = current_user()
    q = Project.query
    if me.role != "admin":
        q = q.filter(Project.members.any(User.id == me.id))
    q = q.filter(Project.is_archived.is_(request.args.get("is_archived") == "true"))
    text = (request.args.get("q") or "").strip()[:100]
    if text:
        q = q.filter(Project.name.ilike(f"%{text}%"))
    return paginate(q.order_by(Project.name), lambda p: p.to_dict())


@bp.post("")
@auth_required("admin")
def create_project():
    v = Validator(json_body())
    name = v.string("name", 2, 120)
    description = v.string("description", 0, 2000, required=False)
    ids = v.id_list("member_ids")
    v.done()
    if Project.query.filter(db.func.lower(Project.name) == name.lower()).first():
        raise ApiError(409, "PROJECT_EXISTS", "A project with this name already exists")
    project = Project(name=name, description=description, created_by=current_user().id)
    project.members = _members(v, ids) or []
    db.session.add(project)
    db.session.commit()
    return ok(project.to_dict(), 201)


@bp.get("/<int:project_id>")
@auth_required()
def get_project(project_id):
    return ok(_visible_or_404(project_id).to_dict())


@bp.patch("/<int:project_id>")
@auth_required("admin")
def update_project(project_id):
    project = _visible_or_404(project_id)
    v = Validator(json_body())
    name = v.string("name", 2, 120, required=False)
    description = v.string("description", 0, 2000, required=False)
    ids = v.id_list("member_ids")
    v.done()
    if name and name.lower() != project.name.lower() and \
            Project.query.filter(db.func.lower(Project.name) == name.lower()).first():
        raise ApiError(409, "PROJECT_EXISTS", "A project with this name already exists")
    if name:
        project.name = name
    if description is not None:
        project.description = description
    members = _members(v, ids)
    if members is not None:
        project.members = members
    db.session.commit()
    return ok(project.to_dict())


@bp.post("/<int:project_id>/archive")
@auth_required("admin")
def archive_project(project_id):
    project = _visible_or_404(project_id)
    project.is_archived = True
    db.session.commit()
    return ok(project.to_dict())
