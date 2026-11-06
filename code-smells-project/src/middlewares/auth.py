"""Guards de autenticação/autorização baseados no token emitido por POST /login."""
from functools import wraps

from flask import current_app, g, request

from src.exceptions import ForbiddenError, UnauthorizedError
from src.models.constants import TIPO_ADMIN


def _usuario_autenticado():
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise UnauthorizedError("Token de autenticação ausente")
    claims = current_app.extensions["token_service"].verificar(token.strip())
    g.usuario = claims
    return claims


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if _usuario_autenticado().get("tipo") != TIPO_ADMIN:
            raise ForbiddenError("Acesso negado")
        return view(*args, **kwargs)
    return wrapper
