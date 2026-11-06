from database import transaction
from models.category import Category
from utils.errors import NotFoundError


class CategoryService:
    def __init__(self, session, categories, tasks):
        self.session = session
        self.categories = categories
        self.tasks = tasks

    def list_with_task_count(self):
        counts = self.tasks.count_by_category()
        return [(category, counts.get(category.id, 0)) for category in self.categories.list_all()]

    def get_category(self, category_id):
        category = self.categories.get(category_id)
        if category is None:
            raise NotFoundError("Categoria não encontrada")
        return category

    def create_category(self, fields):
        category = Category(**fields)
        with transaction(self.session):
            self.categories.add(category)
        return category

    def update_category(self, category_id, fields):
        category = self.get_category(category_id)
        with transaction(self.session):
            for name, value in fields.items():
                setattr(category, name, value)
        return category

    def delete_category(self, category_id):
        category = self.get_category(category_id)
        with transaction(self.session):
            # Tasks must not keep pointing at a category that no longer exists.
            self.tasks.unlink_category(category_id)
            self.categories.delete(category)
