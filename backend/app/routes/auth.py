from flask import Blueprint, current_app
from flask_jwt_extended import create_access_token, get_jwt
from werkzeug.security import check_password_hash, generate_password_hash

from app.errors import ApiError, json_body, ok
from app.extensions import db
from app.models import TokenBlocklist, User
from app.schemas.validators import Validator
from app.security.decorators import auth_required, current_user

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")
_DUMMY_HASH = generate_password_hash("dummy-password-for-timing")  # keeps timing similar for unknown emails


@bp.post("/login")
def login():
    v = Validator(json_body())
    email, password = v.email("email"), v.secret("password")
    v.done()
    user = User.query.filter_by(email=email).first()
    password_ok = check_password_hash(user.password_hash if user else _DUMMY_HASH, password)
    if user is None or not password_ok:
        raise ApiError(401, "INVALID_CREDENTIALS", "Incorrect email or password")
    if not user.is_active:
        raise ApiError(403, "ACCOUNT_DEACTIVATED", "This account is deactivated")
    token = create_access_token(identity=str(user.id))
    expires = int(current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds())
    return ok({"access_token": token, "token_type": "Bearer", "expires_in": expires, "user": user.to_dict()})


@bp.post("/logout")
@auth_required()
def logout():
    db.session.add(TokenBlocklist(jti=get_jwt()["jti"]))
    db.session.commit()
    return ok({"message": "Logged out"})


@bp.get("/me")
@auth_required()
def me():
    return ok(current_user().to_dict())


@bp.patch("/me")
@auth_required()
def update_me():
    v = Validator(json_body())
    name = v.string("name", 2, 100)
    v.done()
    user = current_user()
    user.name = name
    db.session.commit()
    return ok(user.to_dict())


@bp.post("/change-password")
@auth_required()
def change_password():
    v = Validator(json_body())
    current, new = v.secret("current_password"), v.new_password("new_password")
    v.done()
    user = current_user()
    if not user.check_password(current):
        raise ApiError(401, "INVALID_CREDENTIALS", "Current password is incorrect")
    if current == new:
        raise ApiError(422, "VALIDATION_ERROR", "Validation failed", {"new_password": "Must differ from the current password"})
    user.set_password(new)
    db.session.commit()
    return ok({"message": "Password updated"})
