import logging

from database import transaction
from models.constants import DEFAULT_ROLE
from models.user import User
from utils.errors import ConflictError, ForbiddenError, NotFoundError
from utils.validators import validate_role

logger = logging.getLogger(__name__)

ADMIN_ONLY_FIELDS = ("role", "active")


class UserService:
    def __init__(self, session, users, tasks):
        self.session = session
        self.users = users
        self.tasks = tasks

    def list_users_with_task_count(self):
        counts = self.tasks.count_by_user()
        return [(user, counts.get(user.id, 0)) for user in self.users.list_all()]

    def get_user(self, user_id):
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado")
        return user

    def get_user_tasks(self, user_id):
        self.get_user(user_id)
        return self.tasks.list_by_user(user_id)

    def create_user(self, fields, actor=None):
        if self.users.get_by_email(fields["email"]) is not None:
            raise ConflictError("Email já cadastrado")
        role = validate_role(fields["role"])
        if role != DEFAULT_ROLE and not (actor and actor.is_admin()):
            raise ForbiddenError("Apenas administradores podem atribuir este papel")

        user = User(name=fields["name"], email=fields["email"], role=role)
        user.set_password(fields["password"])
        with transaction(self.session):
            self.users.add(user)
        logger.info("Usuário criado: %s", user.id)
        return user

    def update_user(self, user_id, fields, actor):
        user = self.get_user(user_id)
        self._authorize_self_or_admin(user, actor)
        changes_privileges = any(
            field in fields and fields[field] != getattr(user, field) for field in ADMIN_ONLY_FIELDS
        )
        if changes_privileges and not actor.is_admin():
            raise ForbiddenError("Apenas administradores podem alterar papel ou status")
        if "email" in fields:
            existing = self.users.get_by_email(fields["email"])
            if existing is not None and existing.id != user_id:
                raise ConflictError("Email já cadastrado")

        with transaction(self.session):
            for name, value in fields.items():
                if name == "password":
                    user.set_password(value)
                else:
                    setattr(user, name, value)
        return user

    def delete_user(self, user_id, actor):
        user = self.get_user(user_id)
        self._authorize_self_or_admin(user, actor)
        with transaction(self.session):
            self.tasks.delete_by_user(user_id)
            self.users.delete(user)
        logger.info("Usuário deletado: %s", user_id)

    @staticmethod
    def _authorize_self_or_admin(user, actor):
        if actor.id != user.id and not actor.is_admin():
            raise ForbiddenError("Acesso negado")
