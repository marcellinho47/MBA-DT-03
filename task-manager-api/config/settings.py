"""Single place that reads environment variables. No other module reads os.environ."""
import os
import secrets

try:  # python-dotenv is already a declared dependency; .env is optional
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def _bool(name, default="false"):
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def _list(name, default):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


class Settings:
    # Development fallback: random per process (tokens are invalidated on restart).
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    SECRET_KEY_FROM_ENV = bool(os.environ.get("SECRET_KEY"))

    # Relative SQLite paths are resolved by Flask-SQLAlchemy inside ./instance (same file as before).
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///tasks.db")

    DEBUG = _bool("FLASK_DEBUG")
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    CORS_ORIGINS = _list("CORS_ORIGINS", "*")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

    TOKEN_MAX_AGE_SECONDS = int(os.environ.get("TOKEN_MAX_AGE_SECONDS", "86400"))

    # E-mail notifications are only sent when SMTP_HOST is set; otherwise they are logged.
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_SENDER = os.environ.get("SMTP_SENDER", "") or SMTP_USER
    SMTP_USE_TLS = _bool("SMTP_USE_TLS", "true")
