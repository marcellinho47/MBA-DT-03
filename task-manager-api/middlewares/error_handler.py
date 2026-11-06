import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from utils.errors import AppError

logger = logging.getLogger(__name__)

ERROR_KEY = "error"  # same error body format as the original API: {"error": "..."}


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({ERROR_KEY: err.message}), err.status

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        if isinstance(err, HTTPException):  # 404/405/415 from Flask keep their default handling
            return err
        logger.exception("Unhandled error")
        return jsonify({ERROR_KEY: "Erro interno"}), 500
