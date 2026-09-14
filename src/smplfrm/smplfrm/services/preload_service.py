"""Service for managing image cache preload tasks.

Handles admission control, work deduplication, and task dispatch
for asynchronous cache preloading operations.
"""

import hashlib
import logging
from typing import List, Optional

from smplfrm.celery import app
from smplfrm.models import Image, Task
from smplfrm.models.task import TaskType, Status
from smplfrm.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class PreloadConflict(Exception):
    """Raised when preload request conflicts with existing work or capacity."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(detail)


class PreloadService:
    """Service for preload task admission and dispatch."""

    MAX_NON_TERMINAL_TASKS = 5

    def __init__(self):
        self.cache_service = CacheService()

    def create_preload_task(
        self, image_ids: List[str], width: int, height: int
    ) -> Optional[Task]:
        """Create and dispatch a preload task for the given image batch.

        Args:
            image_ids: List of image external IDs to preload
            width: Viewport width in pixels
            height: Viewport height in pixels

        Returns:
            Created Task instance, or None if all images already cached

        Raises:
            PreloadConflict: If work is already in-flight or capacity exceeded
        """
        # Filter to valid images only (skip nonexistent IDs)
        valid_images = list(
            Image.objects.filter(external_id__in=image_ids, deleted=False).values_list(
                "external_id", flat=True
            )
        )

        if not valid_images:
            return None

        # Check if all images are already cached
        all_cached = True
        for image_id in valid_images:
            cache_key = self.cache_service.get_image_cache_key(
                image_id, str(height), str(width)
            )
            if self.cache_service.read(cache_key) is None:
                all_cached = False
                break

        if all_cached:
            logger.debug(
                "All images in batch already cached, skipping preload task creation"
            )
            return None

        # Compute work fingerprint for deduplication
        fingerprint = self._compute_fingerprint(valid_images, width, height)

        # Check for duplicate in-flight work
        duplicate_task = Task.objects.filter(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            status__in=[Status.PENDING, Status.RUNNING],
            payload__fingerprint=fingerprint,
            deleted=False,
        ).first()

        if duplicate_task:
            raise PreloadConflict(
                code="preload_already_in_progress",
                detail="A preload task is already in progress",
            )

        # Check capacity (max 5 non-terminal preload tasks)
        non_terminal_count = Task.objects.filter(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            status__in=[Status.PENDING, Status.RUNNING],
            deleted=False,
        ).count()

        if non_terminal_count >= self.MAX_NON_TERMINAL_TASKS:
            raise PreloadConflict(
                code="preload_capacity_exceeded",
                detail="Maximum concurrent preload tasks reached",
            )

        # Create task with execution payload
        payload = {
            "width": width,
            "height": height,
            "image_ids": valid_images,
            "fingerprint": fingerprint,
        }

        task = Task.objects.create(
            task_type=TaskType.PRELOAD_IMAGE_CACHE, payload=payload
        )

        # Dispatch to Celery worker
        app.send_task("preload_image_cache", kwargs={"task_id": task.external_id})

        logger.info(
            f"Created preload task {task.external_id} for {len(valid_images)} images"
        )

        return task

    def _compute_fingerprint(
        self, image_ids: List[str], width: int, height: int
    ) -> str:
        """Compute deterministic fingerprint for work deduplication.

        Args:
            image_ids: Ordered list of image external IDs
            width: Viewport width
            height: Viewport height

        Returns:
            SHA256 hex digest of the work signature
        """
        # Create a signature that preserves order and includes dimensions
        signature = f"{','.join(image_ids)}|{width}|{height}"
        return hashlib.sha256(signature.encode()).hexdigest()
