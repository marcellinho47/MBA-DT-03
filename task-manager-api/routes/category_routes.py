from flask import Blueprint


def create_category_blueprint(controller):
    bp = Blueprint("categories", __name__)
    bp.add_url_rule("/categories", "list_categories", controller.list_categories, methods=["GET"])
    bp.add_url_rule("/categories", "create_category", controller.create_category, methods=["POST"])
    bp.add_url_rule("/categories/<int:category_id>", "update_category", controller.update_category, methods=["PUT"])
    bp.add_url_rule("/categories/<int:category_id>", "delete_category", controller.delete_category, methods=["DELETE"])
    return bp
