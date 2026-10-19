import os

from flask import Flask
from werkzeug.exceptions import HTTPException

from app.errors import ApiError, error_response
from app.extensions import cors, db, jwt, migrate
from config import BASE_DIR, Config

HTTP_CODES = {400: "BAD_REQUEST", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 413: "PAYLOAD_TOO_LARGE"}


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    os.makedirs(BASE_DIR / "instance", exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
                  allow_headers=["Content-Type", "Authorization"], expose_headers=["Content-Disposition"])

    from app import models  # noqa: F401  (registers tables)
    from app.cli import register_cli
    from app.routes import analysis, auth, dashboard, predictions, projects, reports, tasks, users
    from app.security.jwt_handlers import register_jwt_handlers

    register_jwt_handlers()
    for module in (auth, users, projects, tasks, dashboard, predictions, analysis, reports):
        app.register_blueprint(module.bp)
    register_cli(app)

    @app.errorhandler(ApiError)
    def handle_api_error(e):
        return error_response(e.status, e.code, e.message, e.details)

    @app.errorhandler(HTTPException)
    def handle_http_error(e):
        return error_response(e.code, HTTP_CODES.get(e.code, "HTTP_ERROR"), e.name)

    @app.errorhandler(Exception)
    def handle_unexpected(e):
        app.logger.exception("Unhandled error")
        db.session.rollback()
        return error_response(500, "INTERNAL_ERROR", "Something went wrong on the server")

    @app.get("/api/v1/health")
    def health():
        return {"data": {"status": "ok"}}

    return app
