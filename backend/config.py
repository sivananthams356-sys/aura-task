"""Application configuration. Secrets come from environment variables / .env (never hardcoded)."""
import os
import secrets
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _secret(name):
    value = os.environ.get(name)
    if value:
        return value
    print(f"WARNING: {name} is not set in .env. Using a temporary random value "
          "(logins will reset whenever the server restarts).")
    return secrets.token_hex(32)


class Config:
    SECRET_KEY = _secret("SECRET_KEY")
    JWT_SECRET_KEY = _secret("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.environ.get("JWT_EXPIRES_MINUTES", "60")))
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        "sqlite:///" + str(BASE_DIR / "instance" / "aura_task.db"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = [o.strip() for o in os.environ.get(
        "CORS_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500").split(",") if o.strip()]
    MAX_CODE_BYTES = int(os.environ.get("MAX_CODE_BYTES", "50000"))
    MAX_CODE_LINES = int(os.environ.get("MAX_CODE_LINES", "2000"))
    MAX_CONTENT_LENGTH = 200_000  # reject any request body above ~200 KB


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key-test-secret-key-1234"
    JWT_SECRET_KEY = "test-jwt-secret-key-test-jwt-secret-key-1234"
