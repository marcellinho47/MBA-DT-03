import hashlib
import hmac
import re

from werkzeug.security import check_password_hash, generate_password_hash

from database import db
from models.constants import ADMIN_ROLE, DEFAULT_ROLE
from utils.clock import utcnow

_LEGACY_MD5_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=DEFAULT_ROLE)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def needs_rehash(self):
        return bool(_LEGACY_MD5_PATTERN.match(self.password or ""))

    def check_password(self, raw_password):
        if self.needs_rehash():
            # Legacy unsalted MD5 hash from before the refactor: verified only so that
            # the login flow can immediately re-hash it with a proper KDF.
            legacy_hash = hashlib.md5(raw_password.encode()).hexdigest()
            return hmac.compare_digest(self.password, legacy_hash)
        return check_password_hash(self.password or "", raw_password)

    def is_admin(self):
        return self.role == ADMIN_ROLE
