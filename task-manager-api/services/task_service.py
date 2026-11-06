import logging

from database import transaction
from models.constants import TASK_STATUSES
from models.task import Task
from utils.clock import utcnow
from utils.errors import NotFoundError
from utils.stats import completion_rate

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(self, session, tasks, users, categories, notifier):
        self.session = session
        self.tasks = tasks
        self.users = users
        self.categories = categories
        self.notifier = notifier

    def list_tasks(self):
        return self.tasks.list_all(with_relations=True)

    def get_task(self, task_id):
        task = self.tasks.get(task_id)
        if task is None:
            raise NotFoundError("Task não encontrada")
        return task

    def search(self, text, status, priority, user_id):
        return self.tasks.search(text=text, status=status, priority=priority, user_id=user_id)

    def create_task(self, fields):
        assignee = self._ensure_references(fields.get("user_id"), fields.get("category_id"))
        task = Task(**fields)
        with transaction(self.session):
            self.tasks.add(task)
        logger.info("Task criada: %s", task.id)
        if assignee is not None:
            self.notifier.notify_task_assigned(assignee, task)
        return task

    def update_task(self, task_id, fields):
        task = self.get_task(task_id)
        assignee = self._ensure_references(fields.get("user_id"), fields.get("category_id"))
        reassigned = "user_id" in fields and fields["user_id"] is not None and fields["user_id"] != task.user_id
        with transaction(self.session):  # updated_at is maintained by the column's onupdate
            for name, value in fields.items():
                setattr(task, name, value)
        logger.info("Task atualizada: %s", task.id)
        if reassigned:
            self.notifier.notify_task_assigned(assignee, task)
        return task

    def delete_task(self, task_id):
        task = self.get_task(task_id)
        with transaction(self.session):
            self.tasks.delete(task)
        logger.info("Task deletada: %s", task_id)

    def stats(self):
        by_status = self.tasks.count_by_status()
        total = self.tasks.count()
        stats = {status: by_status.get(status, 0) for status in TASK_STATUSES}
        stats["total"] = total
        stats["overdue"] = len(self.tasks.list_overdue(utcnow()))
        stats["completion_rate"] = completion_rate(stats["done"], total)
        return stats

    def _ensure_references(self, user_id, category_id):
        user = None
        if user_id is not None:
            user = self.users.get(user_id)
            if user is None:
                raise NotFoundError("Usuário não encontrado")
        if category_id is not None and self.categories.get(category_id) is None:
            raise NotFoundError("Categoria não encontrada")
        return user
