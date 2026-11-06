"""Operações de sistema: health check e reset administrativo do banco."""
import logging

from src.database import clear_all_data, transaction

logger = logging.getLogger(__name__)


class SistemaService:
    def __init__(self, conn, produtos, usuarios, pedidos):
        self.conn = conn
        self.produtos = produtos
        self.usuarios = usuarios
        self.pedidos = pedidos

    def contagens(self):
        return {
            "produtos": self.produtos.count(),
            "usuarios": self.usuarios.count(),
            "pedidos": self.pedidos.count(),
        }

    def resetar_banco(self):
        with transaction(self.conn):
            clear_all_data(self.conn)
        logger.warning("Banco de dados resetado por um administrador")
