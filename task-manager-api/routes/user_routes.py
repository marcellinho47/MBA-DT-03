from flask import Blueprint


def create_user_blueprint(controller, auth):
    bp = Blueprint("users", __name__)
    bp.add_url_rule("/users", "list_users", controller.list_users, methods=["GET"])
    bp.add_url_rule("/users", "create_user", auth.optional(controller.create_user), methods=["POST"])
    bp.add_url_rule("/users/<int:user_id>", "get_user", controller.get_user, methods=["GET"])
    bp.add_url_rule("/users/<int:user_id>", "update_user", auth.required(controller.update_user), methods=["PUT"])
    bp.add_url_rule("/users/<int:user_id>", "delete_user", auth.required(controller.delete_user), methods=["DELETE"])
    bp.add_url_rule("/users/<int:user_id>/tasks", "list_user_tasks", controller.list_user_tasks, methods=["GET"])
    return bp
