"""Celery tasks for image cache preloading and stale task recovery.

Preload tasks differ from other core tasks (scan_library, reset_image_count, clear_cache)
in their lifecycle:
- Other tasks: Task created on-demand by service if task_id not provided, uses task_id=None default
- Preload tasks: Task pre-created by PreloadService with execution payload, then dispatched

This pattern supports:
- Admission control (capacity limits, deduplication) before task creation
- Work payload (image_ids, dimensions) stored in Task.payload for worker to read
- Fingerprint-based duplicate detection for in-flight work

Progress is reported through TaskReportingService, consistent with other tasks.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from smplfrm.models.task import TaskType, Status
from smplfrm.services.cache_service import CacheService
from smplfrm.services.image_manipulation_service import ImageManipulationService
from smplfrm.services.image_service import ImageService
from smplfrm.services.task_reporting_service import TaskReportingService
from smplfrm.services.task_service import TaskService

logger = logging.getLogger(__name__)

# Stale threshold: tasks with no status/progress update for this duration are recovered
STALE_THRESHOLD_MINUTES = 10


class PreloadTaskReporter(TaskReportingService):
    """Task reporter for preload operations."""

    def __init__(self):
        super().__init__(task_type=TaskType.PRELOAD_IMAGE_CACHE)


@shared_task(name="preload_image_cache")
def preload_image_cache(task_id: str):
    """Preload image cache for a batch of images.

    Args:
        task_id: External ID of the preload task
    """
    logger.info(f"Starting preload task {task_id}")

    reporter = PreloadTaskReporter()
    task_service = TaskService()
    cache_service = CacheService()
    image_manipulation = ImageManipulationService()
    image_service = ImageService()

    try:
        # Load task and extract payload
        task = task_service.read(task_id)
        payload = task.payload

        width = payload["width"]
        height = payload["height"]
        image_ids = payload["image_ids"]

        total_images = len(image_ids)
        reporter.initiate_task(task_id, total_images)

        processed = 0
        for image_id in image_ids:
            # Check if task was deleted (user cancellation)
            task.refresh_from_db()
            if task.deleted:
                logger.info(f"Preload task {task_id} was cancelled")
                return

            # Resolve image
            try:
                image = image_service.read(image_id)
            except ObjectDoesNotExist:
                # Image deleted after task creation - skip without error
                logger.debug(f"Image {image_id} not found, skipping")
                processed += 1
                reporter.report_task(processed)
                continue

            # Check cache
            cache_key = cache_service.get_image_cache_key(
                image.external_id, str(height), str(width)
            )
            cached_data = cache_service.read(cache_key)

            if cached_data is not None:
                # Already cached - skip
                logger.debug(f"Image {image_id} already cached, skipping")
                processed += 1
                reporter.report_task(processed)
                continue

            # Generate and cache image
            try:
                rendered = image_manipulation.display(image, height, width)
                cache_service.upsert(cache_key, rendered)
                logger.debug(f"Cached image {image_id}")
            except FileNotFoundError:
                # Image file missing - skip without failing entire task
                logger.warning(f"Image file not found for {image_id}, skipping")

            processed += 1
            reporter.report_task(processed)

        reporter.complete_task()
        logger.info(f"Completed preload task {task_id}")

    except Exception as e:
        logger.error(f"Preload task {task_id} failed: {e}", exc_info=True)
        reporter.fail_task("Cache preload failed", exception=e)


@shared_task(name="recover_stale_preload_tasks")
def recover_stale_preload_tasks():
    """Recover stale preload tasks that have not updated in STALE_THRESHOLD_MINUTES.

    Transitions stale pending/running tasks to failed and emits one warning per task.
    This task should run periodically via Celery beat.
    """
    threshold = timezone.now() - timedelta(minutes=STALE_THRESHOLD_MINUTES)
    task_service = TaskService()

    stale_tasks = list(
        task_service.list(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            status__in=[Status.PENDING, Status.RUNNING],
            updated__lt=threshold,
            deleted=False,
        )
    )

    for task in stale_tasks:
        age_minutes = (timezone.now() - task.updated).total_seconds() / 60

        # Emit one sanitized warning with task identity, status, and age
        logger.warning(
            f"Recovering stale preload task {task.external_id}: "
            f"status={task.status}, age={age_minutes:.1f} minutes"
        )

        # Transition to failed
        task_service.fail(
            task,
            error=f"Task became stale after {STALE_THRESHOLD_MINUTES} minutes without update",
        )

    if stale_tasks:
        logger.info(f"Recovered {len(stale_tasks)} stale preload tasks")
