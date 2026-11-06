"""Camada de view: só mapeia URL + método para o controller, com o guard de acesso quando a rota exige."""
from flask import Blueprint

from src.middlewares.auth import require_admin


def build_blueprint(controllers):
    bp = Blueprint("api", __name__)
    produtos, usuarios, pedidos = controllers.produtos, controllers.usuarios, controllers.pedidos
    relatorios, sistema = controllers.relatorios, controllers.sistema

    def rota(path, endpoint, view, method):
        bp.add_url_rule(path, endpoint, view, methods=[method])

    rota("/", "index", sistema.index, "GET")
    rota("/health", "health_check", sistema.health, "GET")

    rota("/produtos", "listar_produtos", produtos.listar, "GET")
    rota("/produtos/busca", "buscar_produtos", produtos.buscar, "GET")
    rota("/produtos/<int:produto_id>", "buscar_produto", produtos.buscar_por_id, "GET")
    rota("/produtos", "criar_produto", require_admin(produtos.criar), "POST")
    rota("/produtos/<int:produto_id>", "atualizar_produto", require_admin(produtos.atualizar), "PUT")
    rota("/produtos/<int:produto_id>", "deletar_produto", require_admin(produtos.deletar), "DELETE")

    rota("/usuarios", "listar_usuarios", require_admin(usuarios.listar), "GET")
    rota("/usuarios/<int:usuario_id>", "buscar_usuario", usuarios.buscar_por_id, "GET")
    rota("/usuarios", "criar_usuario", usuarios.criar, "POST")
    rota("/login", "login", usuarios.login, "POST")

    rota("/pedidos", "criar_pedido", pedidos.criar, "POST")
    rota("/pedidos", "listar_todos_pedidos", require_admin(pedidos.listar_todos), "GET")
    rota("/pedidos/usuario/<int:usuario_id>", "listar_pedidos_usuario", pedidos.listar_por_usuario, "GET")
    rota("/pedidos/<int:pedido_id>/status", "atualizar_status_pedido", require_admin(pedidos.atualizar_status), "PUT")

    rota("/relatorios/vendas", "relatorio_vendas", require_admin(relatorios.vendas), "GET")

    rota("/admin/reset-db", "reset_database", require_admin(sistema.resetar_banco), "POST")
    return bp
