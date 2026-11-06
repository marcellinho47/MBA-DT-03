import logging

from itsdangerous import BadSignature, URLSafeTimedSerializer

from database import transaction
from utils.errors import ForbiddenError, UnauthorizedError

logger = logging.getLogger(__name__)

TOKEN_SALT = "auth-token"


class AuthService:
    """Login and signed bearer tokens (itsdangerous ships with Flask: no new dependency)."""

    def __init__(self, session, users, secret_key, token_max_age):
        self.session = session
        self.users = users
        self.serializer = URLSafeTimedSerializer(secret_key, salt=TOKEN_SALT)
        self.token_max_age = token_max_age

    def login(self, email, password):
        user = self.users.get_by_email(email)
        if user is None or not user.check_password(password):
            raise UnauthorizedError("Credenciais inválidas")
        if not user.active:
            raise ForbiddenError("Usuário inativo")
        if user.needs_rehash():
            with transaction(self.session):
                user.set_password(password)
            logger.info("Legacy password hash upgraded for user %s", user.id)
        return user, self.serializer.dumps({"uid": user.id})

    def user_from_token(self, token):
        try:
            payload = self.serializer.loads(token, max_age=self.token_max_age)
        except BadSignature:  # also covers SignatureExpired
            raise UnauthorizedError("Token inválido ou expirado") from None
        user = self.users.get(payload.get("uid"))
        if user is None or not user.active:
            raise UnauthorizedError("Token inválido ou expirado")
        return user
