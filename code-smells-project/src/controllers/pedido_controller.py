"""Fluxo HTTP de pedidos."""
from flask import jsonify, request

from src.views.serializers import serialize_pedido


class PedidoController:
    def __init__(self, service_factory):
        self._service = service_factory

    def criar(self):
        resultado = self._service().criar(request.get_json(silent=True))
        return jsonify({"dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso"}), 201

    def listar_todos(self):
        pedidos = self._service().listar()
        return jsonify({"dados": [serialize_pedido(p) for p in pedidos], "sucesso": True}), 200

    def listar_por_usuario(self, usuario_id):
        pedidos = self._service().listar(usuario_id)
        return jsonify({"dados": [serialize_pedido(p) for p in pedidos], "sucesso": True}), 200

    def atualizar_status(self, pedido_id):
        self._service().atualizar_status(pedido_id, request.get_json(silent=True))
        return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200
