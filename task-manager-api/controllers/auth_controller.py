from flask import jsonify, request

from utils.validators import validate_login
from views.serializers import user_to_dict


class AuthController:
    def __init__(self, auth_service):
        self.service = auth_service

    def login(self):
        email, password = validate_login(request.get_json())
        user, token = self.service.login(email, password)
        return jsonify({
            "message": "Login realizado com sucesso",
            "user": user_to_dict(user),
            "token": token,
        }), 200
