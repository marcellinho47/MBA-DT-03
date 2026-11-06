from flask import jsonify, request

from utils.validators import validate_category_create, validate_category_update
from views.serializers import category_list_item, category_to_dict


class CategoryController:
    def __init__(self, category_service):
        self.service = category_service

    def list_categories(self):
        categories = self.service.list_with_task_count()
        return jsonify([category_list_item(category, count) for category, count in categories]), 200

    def create_category(self):
        fields = validate_category_create(request.get_json())
        return jsonify(category_to_dict(self.service.create_category(fields))), 201

    def update_category(self, category_id):
        self.service.get_category(category_id)  # 404 before validating the body, as in the original API
        fields = validate_category_update(request.get_json())
        return jsonify(category_to_dict(self.service.update_category(category_id, fields))), 200

    def delete_category(self, category_id):
        self.service.delete_category(category_id)
        return jsonify({"message": "Categoria deletada"}), 200
