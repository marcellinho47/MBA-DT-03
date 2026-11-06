"""Input validation shared by create and update flows. Raises ValidationError (HTTP 400).

Error messages are kept identical to the original API where they already existed.
"""
import re
from datetime import datetime

from models.constants import (
    DEFAULT_CATEGORY_COLOR,
    DEFAULT_PRIORITY,
    DEFAULT_ROLE,
    DEFAULT_TASK_STATUS,
    MAX_PRIORITY,
    MAX_TITLE_LENGTH,
    MIN_PASSWORD_LENGTH,
    MIN_PRIORITY,
    MIN_TITLE_LENGTH,
    TASK_DATE_FORMAT,
    TASK_STATUSES,
    USER_ROLES,
)
from utils.errors import ValidationError

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$")
COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


def require_object(data):
    if not data or not isinstance(data, dict):
        raise ValidationError("Dados inválidos")
    return data


def parse_int(value, message):
    if isinstance(value, bool):
        raise ValidationError(message)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    raise ValidationError(message)


def optional_id(value, message):
    """Foreign-key style ids: falsy means "no reference" (original behaviour)."""
    if value in (None, "", 0):
        return None
    return parse_int(value, message)


# ---------------------------------------------------------------- tasks

def _title(value):
    if not value:
        raise ValidationError("Título é obrigatório")
    if not isinstance(value, str):
        raise ValidationError("Título inválido")
    if len(value) < MIN_TITLE_LENGTH:
        raise ValidationError("Título muito curto")
    if len(value) > MAX_TITLE_LENGTH:
        raise ValidationError("Título muito longo")
    return value


def _status(value):
    if value not in TASK_STATUSES:
        raise ValidationError("Status inválido")
    return value


def parse_priority(value):
    priority = parse_int(value, "Prioridade inválida")
    if not MIN_PRIORITY <= priority <= MAX_PRIORITY:
        raise ValidationError(f"Prioridade deve ser entre {MIN_PRIORITY} e {MAX_PRIORITY}")
    return priority


def _due_date(value, message):
    if not value:
        return None
    if not isinstance(value, str):
        raise ValidationError(message)
    try:
        return datetime.strptime(value, TASK_DATE_FORMAT)
    except ValueError:
        raise ValidationError(message) from None


def _tags(value):
    if isinstance(value, list):
        if not all(isinstance(tag, str) for tag in value):
            raise ValidationError("Tags inválidas")
        return ",".join(value)
    if value is None or isinstance(value, str):
        return value
    raise ValidationError("Tags inválidas")


def _description(value):
    if value is not None and not isinstance(value, str):
        raise ValidationError("Descrição inválida")
    return value


def validate_task_create(data):
    data = require_object(data)
    clean = {
        "title": _title(data.get("title")),
        "description": _description(data.get("description", "")),
        "status": _status(data.get("status", DEFAULT_TASK_STATUS)),
        "priority": parse_priority(data.get("priority", DEFAULT_PRIORITY)),
        "user_id": optional_id(data.get("user_id"), "Usuário inválido"),
        "category_id": optional_id(data.get("category_id"), "Categoria inválida"),
        "due_date": _due_date(data.get("due_date"), "Formato de data inválido. Use YYYY-MM-DD"),
    }
    tags = data.get("tags")
    clean["tags"] = _tags(tags) if tags else None
    return clean


def validate_task_update(data):
    """Only the fields present in the payload are validated and returned."""
    data = require_object(data)
    clean = {}
    if "title" in data:
        clean["title"] = _title(data["title"])
    if "description" in data:
        clean["description"] = _description(data["description"])
    if "status" in data:
        clean["status"] = _status(data["status"])
    if "priority" in data:
        clean["priority"] = parse_priority(data["priority"])
    if "user_id" in data:
        clean["user_id"] = optional_id(data["user_id"], "Usuário inválido")
    if "category_id" in data:
        clean["category_id"] = optional_id(data["category_id"], "Categoria inválida")
    if "due_date" in data:
        clean["due_date"] = _due_date(data["due_date"], "Formato de data inválido")
    if "tags" in data:
        clean["tags"] = _tags(data["tags"])
    return clean


def validate_task_search(args):
    priority = args.get("priority", "")
    user_id = args.get("user_id", "")
    return {
        "text": args.get("q", ""),
        "status": args.get("status", ""),
        "priority": parse_int(priority, "Prioridade inválida") if priority else None,
        "user_id": parse_int(user_id, "Usuário inválido") if user_id else None,
    }


# ---------------------------------------------------------------- users

def _email(value):
    if not isinstance(value, str) or not EMAIL_PATTERN.match(value):
        raise ValidationError("Email inválido")
    return value


def _password(value, message):
    if not isinstance(value, str) or len(value) < MIN_PASSWORD_LENGTH:
        raise ValidationError(message)
    return value


def _role(value):
    if value not in USER_ROLES:
        raise ValidationError("Role inválido")
    return value


def _name(value):
    if not value or not isinstance(value, str):
        raise ValidationError("Nome é obrigatório")
    return value


def validate_user_create(data):
    data = require_object(data)
    name, email, password = data.get("name"), data.get("email"), data.get("password")
    if not name:
        raise ValidationError("Nome é obrigatório")
    if not email:
        raise ValidationError("Email é obrigatório")
    if not password:
        raise ValidationError("Senha é obrigatória")
    return {
        "name": _name(name),
        "email": _email(email),
        "password": _password(password, f"Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres"),
        "role": data.get("role", DEFAULT_ROLE),  # validated by the service (after the e-mail conflict check)
    }


def validate_user_update(data):
    data = require_object(data)
    clean = {}
    if "name" in data:
        clean["name"] = _name(data["name"])
    if "email" in data:
        clean["email"] = _email(data["email"])
    if "password" in data:
        clean["password"] = _password(data["password"], "Senha muito curta")
    if "role" in data:
        clean["role"] = _role(data["role"])
    if "active" in data:
        if not isinstance(data["active"], bool):
            raise ValidationError("Campo active inválido")
        clean["active"] = data["active"]
    return clean


def validate_role(value):
    return _role(value)


def validate_login(data):
    data = require_object(data)
    email, password = data.get("email"), data.get("password")
    if not email or not password or not isinstance(email, str) or not isinstance(password, str):
        raise ValidationError("Email e senha são obrigatórios")
    return email, password


# ---------------------------------------------------------------- categories

def _color(value):
    if not isinstance(value, str) or not COLOR_PATTERN.match(value):
        raise ValidationError("Cor inválida")
    return value


def validate_category_create(data):
    data = require_object(data)
    name = data.get("name")
    if not name or not isinstance(name, str):
        raise ValidationError("Nome é obrigatório")
    return {
        "name": name,
        "description": _description(data.get("description", "")),
        "color": _color(data.get("color", DEFAULT_CATEGORY_COLOR)),
    }


def validate_category_update(data):
    if not isinstance(data, dict):  # an empty object is accepted, as in the original API
        raise ValidationError("Dados inválidos")
    clean = {}
    if "name" in data:
        if not data["name"] or not isinstance(data["name"], str):
            raise ValidationError("Nome é obrigatório")
        clean["name"] = data["name"]
    if "description" in data:
        clean["description"] = _description(data["description"])
    if "color" in data:
        clean["color"] = _color(data["color"])
    return clean
