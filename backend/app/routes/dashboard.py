from flask import Blueprint

from app.errors import ok
from app.security.decorators import auth_required, current_user
from app.services import stats_service

bp = Blueprint("dashboard", __name__, url_prefix="/api/v1/dashboard")


@bp.get("/stats")
@auth_required()
def stats():
    return ok(stats_service.dashboard(current_user()))
