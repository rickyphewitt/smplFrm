from django.db import models

from smplfrm.models.base import ModelBase


class Task(ModelBase):
    """Generic async task with progress tracking."""

    class Status(models.TextChoices):
        PENDING = "pending"
        RUNNING = "running"
        COMPLETED = "completed"
        FAILED = "failed"

    class TaskType(models.TextChoices):
        RESET_IMAGE_COUNT = "reset_image_count"
        CLEAR_CACHE = "clear_cache"
        RESCAN_LIBRARY = "rescan_library"

    task_type = models.CharField(max_length=30, choices=TaskType.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    progress = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True, default="")

    class Meta:
        db_table = "task"
