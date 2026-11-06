from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import selectinload

from models.constants import CLOSED_TASK_STATUSES
from models.task import Task


class TaskRepository:
    def __init__(self, session):
        self.session = session

    def get(self, task_id):
        return self.session.get(Task, task_id)

    def list_all(self, with_relations=False):
        stmt = select(Task).order_by(Task.id)
        if with_relations:
            stmt = stmt.options(selectinload(Task.user), selectinload(Task.category))
        return self.session.scalars(stmt).all()

    def list_by_user(self, user_id):
        return self.session.scalars(select(Task).where(Task.user_id == user_id).order_by(Task.id)).all()

    def search(self, text=None, status=None, priority=None, user_id=None):
        stmt = select(Task)
        if text:
            pattern = f"%{text}%"
            stmt = stmt.where(or_(Task.title.like(pattern), Task.description.like(pattern)))
        if status:
            stmt = stmt.where(Task.status == status)
        if priority is not None:
            stmt = stmt.where(Task.priority == priority)
        if user_id is not None:
            stmt = stmt.where(Task.user_id == user_id)
        return self.session.scalars(stmt.order_by(Task.id)).all()

    def list_overdue(self, now):
        stmt = (
            select(Task)
            .where(
                Task.due_date.is_not(None),
                Task.due_date < now,
                Task.status.not_in(CLOSED_TASK_STATUSES),
            )
            .order_by(Task.id)
        )
        return self.session.scalars(stmt).all()

    def count(self):
        return self.session.scalar(select(func.count(Task.id)))

    def count_by_status(self):
        rows = self.session.execute(select(Task.status, func.count(Task.id)).group_by(Task.status))
        return dict(rows.all())

    def count_by_priority(self):
        rows = self.session.execute(select(Task.priority, func.count(Task.id)).group_by(Task.priority))
        return dict(rows.all())

    def count_by_user(self):
        rows = self.session.execute(
            select(Task.user_id, func.count(Task.id))
            .where(Task.user_id.is_not(None))
            .group_by(Task.user_id)
        )
        return dict(rows.all())

    def count_by_user_and_status(self):
        rows = self.session.execute(
            select(Task.user_id, Task.status, func.count(Task.id))
            .where(Task.user_id.is_not(None))
            .group_by(Task.user_id, Task.status)
        )
        counts = {}
        for user_id, status, total in rows.all():
            counts.setdefault(user_id, {})[status] = total
        return counts

    def count_by_category(self):
        rows = self.session.execute(
            select(Task.category_id, func.count(Task.id))
            .where(Task.category_id.is_not(None))
            .group_by(Task.category_id)
        )
        return dict(rows.all())

    def count_created_since(self, since):
        return self.session.scalar(select(func.count(Task.id)).where(Task.created_at >= since))

    def count_done_since(self, since):
        return self.session.scalar(
            select(func.count(Task.id)).where(Task.status == "done", Task.updated_at >= since)
        )

    def add(self, task):
        self.session.add(task)

    def delete(self, task):
        self.session.delete(task)

    def delete_by_user(self, user_id):
        for task in self.list_by_user(user_id):
            self.session.delete(task)

    def unlink_category(self, category_id):
        self.session.execute(
            update(Task).where(Task.category_id == category_id).values(category_id=None)
        )
