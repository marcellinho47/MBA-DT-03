"""Casos de uso de usuários e autenticação."""
import logging

from src.database import transaction
from src.exceptions import ConflictError, NotFoundError, UnauthorizedError
from src.models.constants import TIPO_CLIENTE
from src.utils.security import hash_password, verify_password
from src.utils.validators import validate_credenciais, validate_novo_usuario

logger = logging.getLogger(__name__)


class UsuarioService:
    def __init__(self, conn, usuarios, tokens):
        self.conn = conn
        self.usuarios = usuarios
        self.tokens = tokens

    def listar(self):
        return self.usuarios.list_all()

    def obter(self, usuario_id):
        usuario = self.usuarios.find_by_id(usuario_id)
        if usuario is None:
            raise NotFoundError("Usuário não encontrado")
        return usuario

    def criar(self, dados):
        campos = validate_novo_usuario(dados)
        with transaction(self.conn):
            if self.usuarios.find_by_email(campos["email"]) is not None:
                raise ConflictError("Email já cadastrado")
            # O cadastro público sempre cria clientes: ninguém se autoatribui papel de admin.
            usuario_id = self.usuarios.create(
                campos["nome"], campos["email"], hash_password(campos["senha"]), TIPO_CLIENTE
            )
        logger.info("Usuário criado: id=%s", usuario_id)
        return usuario_id

    def autenticar(self, dados):
        """Retorna (usuario, token). A senha é conferida com o hash em código, nunca no SQL."""
        email, senha = validate_credenciais(dados)
        usuario = self.usuarios.find_by_email(email)
        if usuario is None or not verify_password(usuario["senha"], senha):
            logger.info("Falha de login")
            raise UnauthorizedError("Email ou senha inválidos")
        logger.info("Login bem-sucedido: id=%s", usuario["id"])
        return usuario, self.tokens.emitir(usuario)
