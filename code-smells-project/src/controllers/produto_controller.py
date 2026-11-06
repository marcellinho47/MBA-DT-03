"""Fluxo HTTP de produtos."""
from flask import jsonify, request

from src.utils.validators import parse_float_param
from src.views.serializers import serialize_produto


class ProdutoController:
    def __init__(self, service_factory):
        self._service = service_factory

    def listar(self):
        produtos = self._service().listar()
        return jsonify({"dados": [serialize_produto(p) for p in produtos], "sucesso": True}), 200

    def buscar_por_id(self, produto_id):
        produto = self._service().obter(produto_id)
        return jsonify({"dados": serialize_produto(produto), "sucesso": True}), 200

    def buscar(self):
        resultados = self._service().buscar(
            termo=request.args.get("q", ""),
            categoria=request.args.get("categoria"),
            preco_min=parse_float_param(request.args.get("preco_min"), "preco_min"),
            preco_max=parse_float_param(request.args.get("preco_max"), "preco_max"),
        )
        return jsonify({
            "dados": [serialize_produto(p) for p in resultados],
            "total": len(resultados),
            "sucesso": True,
        }), 200

    def criar(self):
        produto_id = self._service().criar(request.get_json(silent=True))
        return jsonify({"dados": {"id": produto_id}, "sucesso": True, "mensagem": "Produto criado"}), 201

    def atualizar(self, produto_id):
        self._service().atualizar(produto_id, request.get_json(silent=True))
        return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200

    def deletar(self, produto_id):
        self._service().deletar(produto_id)
        return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200
