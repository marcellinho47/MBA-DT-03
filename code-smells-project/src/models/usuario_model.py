"""Repositório de usuários. Retorna o hash de senha para a camada de serviço, mas os
serializers da view nunca o expõem."""
from src.models.constants import TIPO_CLIENTE

_COLUNAS = "id, nome, email, senha, tipo, criado_em"


def _to_usuario(row):
    return dict(row) if row is not None else None


class UsuarioRepository:
    def __init__(self, conn):
        self.conn = conn

    def list_all(self):
        rows = self.conn.execute(f"SELECT {_COLUNAS} FROM usuarios ORDER BY id").fetchall()
        return [_to_usuario(row) for row in rows]

    def find_by_id(self, usuario_id):
        row = self.conn.execute(f"SELECT {_COLUNAS} FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        return _to_usuario(row)

    def find_by_email(self, email):
        row = self.conn.execute(
            f"SELECT {_COLUNAS} FROM usuarios WHERE lower(email) = lower(?) ORDER BY id LIMIT 1", (email,)
        ).fetchone()
        return _to_usuario(row)

    def create(self, nome, email, senha_hash, tipo=TIPO_CLIENTE):
        cursor = self.conn.execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, senha_hash, tipo),
        )
        return cursor.lastrowid

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
