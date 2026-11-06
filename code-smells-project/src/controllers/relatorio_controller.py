"""Fluxo HTTP de relatórios."""
from flask import jsonify


class RelatorioController:
    def __init__(self, service_factory):
        self._service = service_factory

    def vendas(self):
        return jsonify({"dados": self._service().vendas(), "sucesso": True}), 200
