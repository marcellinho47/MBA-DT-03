from flask import Blueprint


def create_task_blueprint(controller):
    bp = Blueprint("tasks", __name__)
    bp.add_url_rule("/tasks", "list_tasks", controller.list_tasks, methods=["GET"])
    bp.add_url_rule("/tasks", "create_task", controller.create_task, methods=["POST"])
    bp.add_url_rule("/tasks/search", "search_tasks", controller.search_tasks, methods=["GET"])
    bp.add_url_rule("/tasks/stats", "task_stats", controller.task_stats, methods=["GET"])
    bp.add_url_rule("/tasks/<int:task_id>", "get_task", controller.get_task, methods=["GET"])
    bp.add_url_rule("/tasks/<int:task_id>", "update_task", controller.update_task, methods=["PUT"])
    bp.add_url_rule("/tasks/<int:task_id>", "delete_task", controller.delete_task, methods=["DELETE"])
    return bp
