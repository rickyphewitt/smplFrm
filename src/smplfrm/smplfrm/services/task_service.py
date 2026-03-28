import logging
from typing import Any, Dict

from django.db.models import QuerySet

from smplfrm.models import Task
from smplfrm.models.task import Status, TaskType

from .base_service import BaseService

logger = logging.getLogger(__name__)


class TaskService(BaseService):
    """Service for managing async tasks."""

    def create(self, data: Dict[str, Any]) -> Task:
        """Create a new task.

        Args:
            data: Must include 'task_type'

        Returns:
            Created Task instance

        Raises:
            IntegrityError: If a task of the same type is already pending or running
        """
        from django.db import IntegrityError

        task_type = data.get("task_type")
        if Task.objects.filter(
            task_type=task_type,
            status__in=[Status.PENDING, Status.RUNNING],
            deleted=False,
        ).exists():
            raise IntegrityError(
                f"A {TaskType(task_type).label} task is already pending or running."
            )
        return Task.objects.create(**data)

    def read(self, ext_id: str, deleted: bool = False) -> Task:
        """Retrieve a task by external ID.

        Args:
            ext_id: External identifier
            deleted: Whether to include soft-deleted records

        Returns:
            Task instance
        """
        return Task.objects.get(external_id=ext_id, deleted=deleted)

    def list(self, **kwargs) -> QuerySet[Task]:
        """List tasks with optional filtering.

        Args:
            **kwargs: Filter parameters

        Returns:
            QuerySet of Task instances
        """
        if kwargs:
            return Task.objects.filter(**kwargs)
        return Task.objects.all()

    def update(self, task: Task) -> Task:
        """Update an existing task.

        Args:
            task: Task instance to update

        Returns:
            Updated Task instance
        """
        task.save()
        return task

    def delete(self, ext_id: str) -> None:
        """Soft-delete a task. Running tasks will self-cancel on next progress check."""
        task = Task.objects.get(external_id=ext_id)
        task.deleted = True
        task.save()

    def destroy(self, ext_id: str) -> None:
        """Not supported for Task."""
        raise NotImplementedError("Task destruction not supported")

    def start(self, task: Task) -> Task:
        """Mark a task as running.

        Args:
            task: Task instance

        Returns:
            Updated Task instance
        """
        task.status = Task.Status.RUNNING
        task.progress = 0
        return self.update(task)

    def complete(self, task: Task) -> Task:
        """Mark a task as completed.

        Args:
            task: Task instance

        Returns:
            Updated Task instance
        """
        task.status = Task.Status.COMPLETED
        task.progress = 100
        return self.update(task)

    def fail(self, task: Task, error: str = "") -> Task:
        """Mark a task as failed.

        Args:
            task: Task instance
            error: Error message

        Returns:
            Updated Task instance
        """
        task.status = Task.Status.FAILED
        task.error = error
        return self.update(task)

    def update_progress(self, task: Task, progress: int) -> Task:
        """Update task progress.

        Args:
            task: Task instance
            progress: Progress percentage (0-100)

        Returns:
            Updated Task instance
        """
        task.progress = min(progress, 100)
        return self.update(task)

    def clear_old_tasks(self):
        from datetime import timedelta

        from django.utils import timezone

        task_age = timezone.now() - timedelta(days=7)
        tasks_to_delete = Task.objects.filter(created__lt=task_age)
        logger.info(f"Deleting old: {tasks_to_delete.count()} tasks.")
        tasks_to_delete.delete()
