"""Fluxo HTTP de endpoints de sistema: índice, health check e reset administrativo."""
import logging

from flask import jsonify

from src.config.settings import APP_VERSION
from src.exceptions import ForbiddenError

logger = logging.getLogger(__name__)


class SistemaController:
    def __init__(self, service_factory, app_env, reset_habilitado):
        self._service = service_factory
        self._app_env = app_env
        self._reset_habilitado = reset_habilitado

    def index(self):
        return jsonify({
            "mensagem": "Bem-vindo à API da Loja",
            "versao": APP_VERSION,
            "endpoints": {
                "produtos": "/produtos",
                "usuarios": "/usuarios",
                "pedidos": "/pedidos",
                "login": "/login",
                "relatorios": "/relatorios/vendas",
                "health": "/health",
            },
        })

    def health(self):
        # O health check precisa responder com seu próprio formato mesmo com o banco fora do ar.
        try:
            contagens = self._service().contagens()
        except Exception:
            logger.exception("Health check falhou")
            return jsonify({"status": "erro", "detalhes": "Banco de dados indisponível"}), 500
        return jsonify({
            "status": "ok",
            "database": "connected",
            "counts": contagens,
            "versao": APP_VERSION,
            "ambiente": self._app_env,
        }), 200

    def resetar_banco(self):
        if not self._reset_habilitado:
            raise ForbiddenError("Reset do banco desabilitado (defina ENABLE_ADMIN_RESET=true)")
        self._service().resetar_banco()
        return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200
