"""Casos de uso de pedidos: criação transacional com baixa de estoque e mudança de status."""
from collections import defaultdict

from src.database import transaction
from src.exceptions import NotFoundError, ValidationError
from src.utils.validators import validate_pedido, validate_status


class PedidoService:
    def __init__(self, conn, pedidos, produtos, notifier):
        self.conn = conn
        self.pedidos = pedidos
        self.produtos = produtos
        self.notifier = notifier

    def criar(self, dados):
        usuario_id, itens = validate_pedido(dados)

        # BEGIN IMMEDIATE: a checagem de estoque e a baixa acontecem sob o mesmo lock de escrita.
        with transaction(self.conn):
            produtos = self.produtos.find_by_ids({item["produto_id"] for item in itens})
            reservado = defaultdict(int)
            total = 0
            for item in itens:
                produto = produtos.get(item["produto_id"])
                if produto is None:
                    raise ValidationError(f"Produto {item['produto_id']} não encontrado")
                reservado[produto["id"]] += item["quantidade"]
                if produto["estoque"] < reservado[produto["id"]]:
                    raise ValidationError(f"Estoque insuficiente para {produto['nome']}")
                total += produto["preco"] * item["quantidade"]

            pedido_id = self.pedidos.create(usuario_id, total)
            for item in itens:
                produto = produtos[item["produto_id"]]
                self.pedidos.add_item(pedido_id, produto["id"], item["quantidade"], produto["preco"])
                if not self.produtos.decrement_stock(produto["id"], item["quantidade"]):
                    raise ValidationError(f"Estoque insuficiente para {produto['nome']}")

        self.notifier.pedido_criado(pedido_id, usuario_id)
        return {"pedido_id": pedido_id, "total": total}

    def listar(self, usuario_id=None):
        return self.pedidos.list_with_items(usuario_id)

    def atualizar_status(self, pedido_id, dados):
        status = validate_status(dados)
        with transaction(self.conn):
            if self.pedidos.find_by_id(pedido_id) is None:
                raise NotFoundError("Pedido não encontrado")
            self.pedidos.update_status(pedido_id, status)
        self.notifier.status_alterado(pedido_id, status)
