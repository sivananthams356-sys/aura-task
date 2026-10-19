"""Backend-enforced authentication + role checks. Frontend hiding is never relied on."""
from functools import wraps

from flask import g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.errors import ApiError
from app.extensions import db
from app.models import User


def auth_required(*roles):
    """Require a valid token, an active account and (optionally) one of the given roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = db.session.get(User, int(get_jwt_identity()))
            if user is None:
                raise ApiError(401, "UNAUTHORIZED", "Authentication required")
            if not user.is_active:
                raise ApiError(403, "ACCOUNT_DEACTIVATED", "This account is deactivated")
            if roles and user.role not in roles:
                raise ApiError(403, "FORBIDDEN", "You do not have permission to perform this action")
            g.current_user = user
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def current_user():
    return g.current_user
