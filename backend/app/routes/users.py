from flask import Blueprint, request

from app.errors import ApiError, json_body, ok, paginate
from app.extensions import db
from app.models import ROLES, User
from app.schemas.validators import Validator
from app.security.decorators import auth_required, current_user
from app.services.access import can_view_user

bp = Blueprint("users", __name__, url_prefix="/api/v1/users")


def _get_user_or_404(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        raise ApiError(404, "NOT_FOUND", "User not found")
    return user


def _check_manager(manager_id, v):
    manager = db.session.get(User, manager_id) if manager_id is not None else None
    if manager is None or manager.role != "manager" or not manager.is_active:
        v.fail("manager_id", "Must be the id of an active manager")
    return manager


@bp.get("")
@auth_required("admin", "manager")
def list_users():
    me = current_user()
    q = User.query
    if me.role == "manager":
        q = q.filter(User.manager_id == me.id)
    role = request.args.get("role")
    if role in ROLES:
        q = q.filter(User.role == role)
    active = request.args.get("is_active")
    if active in ("true", "false"):
        q = q.filter(User.is_active.is_(active == "true"))
    text = (request.args.get("q") or "").strip()[:100]
    if text:
        like = f"%{text}%"
        q = q.filter(db.or_(User.name.ilike(like), User.email.ilike(like)))
    return paginate(q.order_by(User.name), lambda u: u.to_dict())


@bp.post("")
@auth_required("admin")
def create_user():
    v = Validator(json_body())
    name, email = v.string("name", 2, 100), v.email("email")
    password, role = v.new_password("password"), v.enum("role", ROLES)
    manager_id = v.integer("manager_id", required=(role == "employee"))
    v.done()
    if email and User.query.filter_by(email=email).first():
        raise ApiError(409, "EMAIL_EXISTS", "A user with this email already exists")
    if role == "employee":
        _check_manager(manager_id, v)
        v.done()
    else:
        manager_id = None
    user = User(name=name, email=email, role=role, manager_id=manager_id)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return ok(user.to_dict(), 201)


@bp.get("/<int:user_id>")
@auth_required()
def get_user(user_id):
    user = _get_user_or_404(user_id)
    if not can_view_user(current_user(), user):
        raise ApiError(404, "NOT_FOUND", "User not found")
    return ok(user.to_dict())


@bp.patch("/<int:user_id>")
@auth_required("admin")
def update_user(user_id):
    user = _get_user_or_404(user_id)
    v = Validator(json_body())
    name = v.string("name", 2, 100, required=False)
    role = v.enum("role", ROLES, required=False)
    manager_id = v.integer("manager_id", required=False)
    v.done()
    new_role = role or user.role
    if role and role != user.role:
        if user.id == current_user().id:
            raise ApiError(409, "CANNOT_CHANGE_OWN_ROLE", "You cannot change your own role")
        if user.role == "manager" and User.query.filter_by(manager_id=user.id).count():
            raise ApiError(409, "REASSIGN_TEAM_FIRST", "Reassign this manager's team members first")
    if new_role == "employee":
        manager_id = manager_id if manager_id is not None else user.manager_id
        _check_manager(manager_id, v)
        v.done()
    else:
        manager_id = None
    if name:
        user.name = name
    user.role, user.manager_id = new_role, manager_id
    db.session.commit()
    return ok(user.to_dict())


@bp.post("/<int:user_id>/deactivate")
@auth_required("admin")
def deactivate(user_id):
    user = _get_user_or_404(user_id)
    if user.id == current_user().id:
        raise ApiError(409, "CANNOT_DEACTIVATE_SELF", "You cannot deactivate your own account")
    user.is_active = False
    db.session.commit()
    return ok(user.to_dict())


@bp.post("/<int:user_id>/activate")
@auth_required("admin")
def activate(user_id):
    user = _get_user_or_404(user_id)
    user.is_active = True
    db.session.commit()
    return ok(user.to_dict())


@bp.post("/<int:user_id>/reset-password")
@auth_required("admin")
def reset_password(user_id):
    user = _get_user_or_404(user_id)
    v = Validator(json_body())
    password = v.new_password("new_password")
    v.done()
    user.set_password(password)
    db.session.commit()
    return ok({"message": "Password reset"})
