"""Application factory: carrega a config, inicializa o banco, injeta as dependências e registra
rotas e error handlers."""
import logging
from types import SimpleNamespace

from flask import Flask
from flask_cors import CORS

from src import database
from src.config.settings import load_settings
from src.controllers.pedido_controller import PedidoController
from src.controllers.produto_controller import ProdutoController
from src.controllers.relatorio_controller import RelatorioController
from src.controllers.sistema_controller import SistemaController
from src.controllers.usuario_controller import UsuarioController
from src.database import get_db
from src.middlewares.error_handler import register_error_handlers
from src.models.pedido_model import PedidoRepository
from src.models.produto_model import ProdutoRepository
from src.models.usuario_model import UsuarioRepository
from src.services.notification_service import NotificationService
from src.services.pedido_service import PedidoService
from src.services.produto_service import ProdutoService
from src.services.relatorio_service import RelatorioService
from src.services.sistema_service import SistemaService
from src.services.token_service import TokenService
from src.services.usuario_service import UsuarioService
from src.views.routes import build_blueprint

logger = logging.getLogger(__name__)


def _build_controllers(settings, tokens, notifier):
    """Cada factory monta o service sobre a conexão da requisição atual."""

    def produto_service():
        conn = get_db()
        return ProdutoService(conn, ProdutoRepository(conn))

    def usuario_service():
        conn = get_db()
        return UsuarioService(conn, UsuarioRepository(conn), tokens)

    def pedido_service():
        conn = get_db()
        return PedidoService(conn, PedidoRepository(conn), ProdutoRepository(conn), notifier)

    def relatorio_service():
        return RelatorioService(PedidoRepository(get_db()))

    def sistema_service():
        conn = get_db()
        return SistemaService(conn, ProdutoRepository(conn), UsuarioRepository(conn), PedidoRepository(conn))

    return SimpleNamespace(
        produtos=ProdutoController(produto_service),
        usuarios=UsuarioController(usuario_service),
        pedidos=PedidoController(pedido_service),
        relatorios=RelatorioController(relatorio_service),
        sistema=SistemaController(sistema_service, settings["APP_ENV"], settings["ENABLE_ADMIN_RESET"]),
    )


def create_app(overrides=None):
    settings = load_settings()
    if overrides:
        settings.update(overrides)

    logging.basicConfig(level=settings["LOG_LEVEL"], format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = Flask(__name__)
    app.config.from_mapping(settings)

    if settings["SECRET_KEY_IS_EPHEMERAL"]:
        logger.warning("SECRET_KEY não definida: usando chave efêmera (tokens perdem validade a cada reinício)")
    if settings["CORS_ORIGINS"]:
        CORS(app, origins=settings["CORS_ORIGINS"])

    database.init_app(app)

    tokens = TokenService(settings["SECRET_KEY"], settings["TOKEN_MAX_AGE"])
    app.extensions["token_service"] = tokens

    controllers = _build_controllers(settings, tokens, NotificationService())
    app.register_blueprint(build_blueprint(controllers))
    register_error_handlers(app)
    return app
