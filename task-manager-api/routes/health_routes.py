from flask import Blueprint


def create_health_blueprint(controller):
    bp = Blueprint("health", __name__)
    bp.add_url_rule("/", "index", controller.index, methods=["GET"])
    bp.add_url_rule("/health", "health", controller.health, methods=["GET"])
    return bp
