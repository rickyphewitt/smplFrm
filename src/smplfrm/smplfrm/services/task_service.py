import logging
from typing import Any, Dict

from django.db.models import QuerySet

from smplfrm.models import Task

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
        """
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
        """Not supported for Task."""
        raise NotImplementedError("Task deletion not supported")

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
