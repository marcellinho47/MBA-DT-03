from contextlib import contextmanager

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


@contextmanager
def transaction(session):
    """Unit of work: commit on success, rollback and re-raise on any error."""
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise


def init_database(app):
    db.init_app(app)
    with app.app_context():
        import models  # noqa: F401  (registers the entities before create_all)

        db.create_all()
