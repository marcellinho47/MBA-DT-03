"""Configuração da aplicação: o único módulo que lê variáveis de ambiente."""
import os
import secrets
from pathlib import Path

APP_VERSION = "1.0.0"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _env_list(name):
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


def load_settings():
    """Lê a configuração do ambiente. Defaults seguros, pensados para desenvolvimento local."""
    secret_key = os.environ.get("SECRET_KEY")
    return {
        # Sem SECRET_KEY definida, gera uma chave efêmera: tokens deixam de valer a cada reinício.
        "SECRET_KEY": secret_key or secrets.token_hex(32),
        "SECRET_KEY_IS_EPHEMERAL": not secret_key,
        "DEBUG": _env_bool("FLASK_DEBUG"),
        "APP_ENV": os.environ.get("APP_ENV", "development"),
        "HOST": os.environ.get("HOST", "127.0.0.1"),
        "PORT": int(os.environ.get("PORT", "5000")),
        "DATABASE_PATH": os.environ.get("DATABASE_PATH", str(PROJECT_ROOT / "loja.db")),
        # Vazio = sem cabeçalhos CORS (somente mesma origem). Use "*" ou uma lista separada por vírgula.
        "CORS_ORIGINS": _env_list("CORS_ORIGINS"),
        "TOKEN_MAX_AGE": int(os.environ.get("TOKEN_MAX_AGE", "3600")),
        "ENABLE_ADMIN_RESET": _env_bool("ENABLE_ADMIN_RESET"),
        "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO").upper(),
    }
