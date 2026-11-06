from flask import Blueprint


def create_auth_blueprint(controller):
    bp = Blueprint("auth", __name__)
    bp.add_url_rule("/login", "login", controller.login, methods=["POST"])
    return bp
