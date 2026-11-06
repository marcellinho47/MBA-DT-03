"""Casos de uso de produtos."""
import logging

from src.database import transaction
from src.exceptions import NotFoundError
from src.utils.validators import validate_produto

logger = logging.getLogger(__name__)


class ProdutoService:
    def __init__(self, conn, produtos):
        self.conn = conn
        self.produtos = produtos

    def listar(self):
        return self.produtos.list_all()

    def obter(self, produto_id):
        produto = self.produtos.find_by_id(produto_id)
        if produto is None:
            raise NotFoundError("Produto não encontrado")
        return produto

    def buscar(self, termo, categoria, preco_min, preco_max):
        return self.produtos.search(termo, categoria, preco_min, preco_max)

    def criar(self, dados):
        campos = validate_produto(dados)
        with transaction(self.conn):
            produto_id = self.produtos.create(**campos)
        logger.info("Produto criado com ID %s", produto_id)
        return produto_id

    def atualizar(self, produto_id, dados):
        self.obter(produto_id)
        campos = validate_produto(dados)
        with transaction(self.conn):
            self.produtos.update(produto_id, **campos)

    def deletar(self, produto_id):
        self.obter(produto_id)
        with transaction(self.conn):
            self.produtos.delete(produto_id)
        logger.info("Produto %s deletado", produto_id)
