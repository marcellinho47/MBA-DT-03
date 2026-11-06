"""Hash de senha com KDF (Werkzeug já vem com o Flask, então não há dependência nova)."""
from werkzeug.security import check_password_hash, generate_password_hash

_HASH_PREFIXES = ("scrypt:", "pbkdf2:")


def hash_password(raw):
    return generate_password_hash(raw)


def verify_password(stored_hash, raw):
    if not stored_hash or not is_password_hash(stored_hash):
        return False
    return check_password_hash(stored_hash, raw)


def is_password_hash(value):
    return isinstance(value, str) and value.startswith(_HASH_PREFIXES)
