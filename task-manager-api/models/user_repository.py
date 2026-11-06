from sqlalchemy import func, select

from models.user import User


class UserRepository:
    def __init__(self, session):
        self.session = session

    def get(self, user_id):
        return self.session.get(User, user_id)

    def get_by_email(self, email):
        return self.session.scalar(select(User).where(User.email == email))

    def list_all(self):
        return self.session.scalars(select(User).order_by(User.id)).all()

    def count(self):
        return self.session.scalar(select(func.count(User.id)))

    def add(self, user):
        self.session.add(user)

    def delete(self, user):
        self.session.delete(user)
