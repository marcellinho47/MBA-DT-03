from functools import wraps

from flask import g, request

from utils.errors import UnauthorizedError

BEARER_PREFIX = "Bearer "


class AuthMiddleware:
    """Resolves the bearer token into ``g.current_user``.

    ``optional`` lets anonymous requests through (current_user = None);
    ``required`` rejects them with 401.
    """

    def __init__(self, auth_service):
        self.auth_service = auth_service

    def _load_user(self):
        header = request.headers.get("Authorization", "")
        if not header:
            return None
        if not header.startswith(BEARER_PREFIX):
            raise UnauthorizedError("Token inválido ou expirado")
        return self.auth_service.user_from_token(header[len(BEARER_PREFIX):].strip())

    def optional(self, view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            g.current_user = self._load_user()
            return view(*args, **kwargs)

        return wrapper

    def required(self, view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            g.current_user = self._load_user()
            if g.current_user is None:
                raise UnauthorizedError("Autenticação necessária")
            return view(*args, **kwargs)

        return wrapper
