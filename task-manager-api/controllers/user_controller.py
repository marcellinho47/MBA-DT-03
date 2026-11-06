from flask import g, jsonify, request

from utils.clock import utcnow
from utils.validators import validate_user_create, validate_user_update
from views.serializers import user_detail, user_list_item, user_task_item, user_to_dict


class UserController:
    def __init__(self, user_service):
        self.service = user_service

    def list_users(self):
        users = self.service.list_users_with_task_count()
        return jsonify([user_list_item(user, count) for user, count in users]), 200

    def get_user(self, user_id):
        user = self.service.get_user(user_id)
        return jsonify(user_detail(user, self.service.get_user_tasks(user_id))), 200

    def create_user(self):
        fields = validate_user_create(request.get_json())
        user = self.service.create_user(fields, actor=g.current_user)
        return jsonify(user_to_dict(user)), 201

    def update_user(self, user_id):
        self.service.get_user(user_id)  # 404 before validating the body, as in the original API
        fields = validate_user_update(request.get_json())
        user = self.service.update_user(user_id, fields, actor=g.current_user)
        return jsonify(user_to_dict(user)), 200

    def delete_user(self, user_id):
        self.service.delete_user(user_id, actor=g.current_user)
        return jsonify({"message": "Usuário deletado com sucesso"}), 200

    def list_user_tasks(self, user_id):
        now = utcnow()
        tasks = self.service.get_user_tasks(user_id)
        return jsonify([user_task_item(task, now) for task in tasks]), 200
