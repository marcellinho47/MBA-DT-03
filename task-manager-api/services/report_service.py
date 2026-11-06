from datetime import timedelta

from models.constants import HIGH_PRIORITY_MAX, PRIORITY_LABELS, RECENT_ACTIVITY_DAYS, TASK_STATUSES
from utils.clock import utcnow
from utils.errors import NotFoundError
from utils.stats import completion_rate


class ReportService:
    def __init__(self, tasks, users, categories):
        self.tasks = tasks
        self.users = users
        self.categories = categories

    def summary(self):
        now = utcnow()
        since = now - timedelta(days=RECENT_ACTIVITY_DAYS)
        by_status = self.tasks.count_by_status()
        by_priority = self.tasks.count_by_priority()
        overdue_tasks = self.tasks.list_overdue(now)
        per_user = self.tasks.count_by_user_and_status()

        user_productivity = []
        for user in self.users.list_all():
            status_counts = per_user.get(user.id, {})
            total = sum(status_counts.values())
            completed = status_counts.get("done", 0)
            user_productivity.append({
                "user_id": user.id,
                "user_name": user.name,
                "total_tasks": total,
                "completed_tasks": completed,
                "completion_rate": completion_rate(completed, total),
            })

        return {
            "generated_at": str(now),
            "overview": {
                "total_tasks": self.tasks.count(),
                "total_users": self.users.count(),
                "total_categories": self.categories.count(),
            },
            "tasks_by_status": {status: by_status.get(status, 0) for status in TASK_STATUSES},
            "tasks_by_priority": {
                label: by_priority.get(priority, 0) for priority, label in PRIORITY_LABELS.items()
            },
            "overdue": {
                "count": len(overdue_tasks),
                "tasks": [
                    {
                        "id": task.id,
                        "title": task.title,
                        "due_date": str(task.due_date),
                        "days_overdue": (now - task.due_date).days,
                    }
                    for task in overdue_tasks
                ],
            },
            "recent_activity": {
                "tasks_created_last_7_days": self.tasks.count_created_since(since),
                "tasks_completed_last_7_days": self.tasks.count_done_since(since),
            },
            "user_productivity": user_productivity,
        }

    def user_report(self, user_id):
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado")
        tasks = self.tasks.list_by_user(user_id)
        now = utcnow()
        statistics = {status: 0 for status in TASK_STATUSES}
        for task in tasks:
            if task.status in statistics:
                statistics[task.status] += 1
        statistics["total_tasks"] = len(tasks)
        statistics["overdue"] = sum(1 for task in tasks if task.is_overdue(now))
        statistics["high_priority"] = sum(1 for task in tasks if task.priority <= HIGH_PRIORITY_MAX)
        statistics["completion_rate"] = completion_rate(statistics["done"], len(tasks))
        return {
            "user": {"id": user.id, "name": user.name, "email": user.email},
            "statistics": statistics,
        }
