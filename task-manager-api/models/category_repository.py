from sqlalchemy import func, select

from models.category import Category


class CategoryRepository:
    def __init__(self, session):
        self.session = session

    def get(self, category_id):
        return self.session.get(Category, category_id)

    def list_all(self):
        return self.session.scalars(select(Category).order_by(Category.id)).all()

    def count(self):
        return self.session.scalar(select(func.count(Category.id)))

    def add(self, category):
        self.session.add(category)

    def delete(self, category):
        self.session.delete(category)
