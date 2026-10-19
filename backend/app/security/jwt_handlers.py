from app.errors import error_response
from app.extensions import db, jwt
from app.models import TokenBlocklist


def register_jwt_handlers():
    @jwt.token_in_blocklist_loader
    def is_revoked(_header, payload):
        return db.session.query(TokenBlocklist.id).filter_by(jti=payload["jti"]).first() is not None

    @jwt.unauthorized_loader
    def missing_token(_reason):
        return error_response(401, "UNAUTHORIZED", "Authentication required")

    @jwt.invalid_token_loader
    def invalid_token(_reason):
        return error_response(401, "UNAUTHORIZED", "Invalid token")

    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        return error_response(401, "UNAUTHORIZED", "Session expired, please log in again")

    @jwt.revoked_token_loader
    def revoked_token(_header, _payload):
        return error_response(401, "UNAUTHORIZED", "Token has been revoked")
