from routes.auth_routes import create_auth_blueprint
from routes.category_routes import create_category_blueprint
from routes.health_routes import create_health_blueprint
from routes.report_routes import create_report_blueprint
from routes.task_routes import create_task_blueprint
from routes.user_routes import create_user_blueprint


def register_routes(app, controllers, auth):
    """View layer: maps URL + method to controller actions. No logic here."""
    app.register_blueprint(create_health_blueprint(controllers["health"]))
    app.register_blueprint(create_task_blueprint(controllers["tasks"]))
    app.register_blueprint(create_user_blueprint(controllers["users"], auth))
    app.register_blueprint(create_auth_blueprint(controllers["auth"]))
    app.register_blueprint(create_category_blueprint(controllers["categories"]))
    app.register_blueprint(create_report_blueprint(controllers["reports"]))
