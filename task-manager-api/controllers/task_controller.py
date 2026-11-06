from flask import jsonify, request

from utils.clock import utcnow
from utils.validators import validate_task_create, validate_task_search, validate_task_update
from views.serializers import task_detail, task_list_item, task_to_dict


class TaskController:
    def __init__(self, task_service):
        self.service = task_service

    def list_tasks(self):
        now = utcnow()
        return jsonify([task_list_item(task, now) for task in self.service.list_tasks()]), 200

    def get_task(self, task_id):
        return jsonify(task_detail(self.service.get_task(task_id))), 200

    def create_task(self):
        fields = validate_task_create(request.get_json())
        return jsonify(task_to_dict(self.service.create_task(fields))), 201

    def update_task(self, task_id):
        self.service.get_task(task_id)  # 404 before validating the body, as in the original API
        fields = validate_task_update(request.get_json())
        return jsonify(task_to_dict(self.service.update_task(task_id, fields))), 200

    def delete_task(self, task_id):
        self.service.delete_task(task_id)
        return jsonify({"message": "Task deletada com sucesso"}), 200

    def search_tasks(self):
        filters = validate_task_search(request.args)
        return jsonify([task_to_dict(task) for task in self.service.search(**filters)]), 200

    def task_stats(self):
        return jsonify(self.service.stats()), 200
