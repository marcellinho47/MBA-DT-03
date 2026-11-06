"""Composition root: builds the application and wires its dependencies. No business logic."""
import logging

from flask import Flask
from flask_cors import CORS

from config import Settings
from controllers.auth_controller import AuthController
from controllers.category_controller import CategoryController
from controllers.health_controller import HealthController
from controllers.report_controller import ReportController
from controllers.task_controller import TaskController
from controllers.user_controller import UserController
from database import db, init_database
from middlewares.auth import AuthMiddleware
from middlewares.error_handler import register_error_handlers
from models.category_repository import CategoryRepository
from models.task_repository import TaskRepository
from models.user_repository import UserRepository
from routes import register_routes
from services.auth_service import AuthService
from services.category_service import CategoryService
from services.notification_service import LogEmailSender, NotificationService, SmtpEmailSender
from services.report_service import ReportService
from services.task_service import TaskService
from services.user_service import UserService

logger = logging.getLogger(__name__)


def build_email_sender(settings):
    if not settings.SMTP_HOST:
        return LogEmailSender()
    return SmtpEmailSender(
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        sender=settings.SMTP_SENDER,
        use_tls=settings.SMTP_USE_TLS,
    )


def create_app(settings=Settings):
    logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=settings.SECRET_KEY,
        SQLALCHEMY_DATABASE_URI=settings.DATABASE_URL,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if not settings.SECRET_KEY_FROM_ENV:
        logger.warning("SECRET_KEY not set: using an ephemeral key (tokens are lost on restart)")

    CORS(app, origins=settings.CORS_ORIGINS)
    init_database(app)

    session = db.session
    tasks = TaskRepository(session)
    users = UserRepository(session)
    categories = CategoryRepository(session)

    notifier = NotificationService(build_email_sender(settings))
    auth_service = AuthService(session, users, settings.SECRET_KEY, settings.TOKEN_MAX_AGE_SECONDS)

    controllers = {
        "health": HealthController(),
        "tasks": TaskController(TaskService(session, tasks, users, categories, notifier)),
        "users": UserController(UserService(session, users, tasks)),
        "auth": AuthController(auth_service),
        "categories": CategoryController(CategoryService(session, categories, tasks)),
        "reports": ReportController(ReportService(tasks, users, categories)),
    }
    register_routes(app, controllers, AuthMiddleware(auth_service))
    register_error_handlers(app)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG)
