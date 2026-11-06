"""Tokens de autenticação assinados com a SECRET_KEY. Usa itsdangerous, que já é dependência do Flask."""
from itsdangerous import BadSignature, URLSafeTimedSerializer

from src.exceptions import UnauthorizedError


class TokenService:
    def __init__(self, secret_key, max_age):
        self._serializer = URLSafeTimedSerializer(secret_key, salt="auth-token")
        self._max_age = max_age

    def emitir(self, usuario):
        return self._serializer.dumps({"id": usuario["id"], "tipo": usuario["tipo"]})

    def verificar(self, token):
        try:
            return self._serializer.loads(token, max_age=self._max_age)
        except BadSignature:  # inclui SignatureExpired
            raise UnauthorizedError("Token inválido ou expirado") from None
