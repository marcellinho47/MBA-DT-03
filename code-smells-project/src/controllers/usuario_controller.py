"""Fluxo HTTP de usuários e login."""
from flask import jsonify, request

from src.views.serializers import serialize_usuario, serialize_usuario_autenticado


class UsuarioController:
    def __init__(self, service_factory):
        self._service = service_factory

    def listar(self):
        usuarios = self._service().listar()
        return jsonify({"dados": [serialize_usuario(u) for u in usuarios], "sucesso": True}), 200

    def buscar_por_id(self, usuario_id):
        usuario = self._service().obter(usuario_id)
        return jsonify({"dados": serialize_usuario(usuario), "sucesso": True}), 200

    def criar(self):
        usuario_id = self._service().criar(request.get_json(silent=True))
        return jsonify({"dados": {"id": usuario_id}, "sucesso": True}), 201

    def login(self):
        usuario, token = self._service().autenticar(request.get_json(silent=True))
        return jsonify({
            "dados": serialize_usuario_autenticado(usuario),
            "token": token,
            "sucesso": True,
            "mensagem": "Login OK",
        }), 200
