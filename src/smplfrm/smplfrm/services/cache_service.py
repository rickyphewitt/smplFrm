import logging
from typing import Any, Optional

from django.core.cache import cache
from django.conf import settings

from smplfrm.services.task_reporting_service import TaskReportingService
from smplfrm.models.task import TaskType

logger = logging.getLogger(__name__)


class CacheService(TaskReportingService):
    """Service for managing cache operations."""

    def __init__(self) -> None:
        super().__init__(task_type=TaskType.CLEAR_CACHE)
        self.cache = cache

    def _get_cache_timeout(self) -> int:
        from smplfrm.services.config_service import ConfigService

        return ConfigService().load_config().image_cache_timeout

    def upsert(
        self, cache_key: str, cache_data: Any, expires: Optional[int] = None
    ) -> None:
        """Update or insert an item for a given key.

        Args:
            cache_key: Key to store the data under
            cache_data: Data to cache
            expires: Expiration time in seconds, defaults to SMPL_FRM_IMAGE_CACHE_TIMEOUT
        """
        if expires is None:
            expires = self._get_cache_timeout()
        self.cache.set(key=cache_key, value=cache_data, timeout=expires)

    def read(self, cache_key: str) -> Any:
        """Retrieve cached data by key.

        Args:
            cache_key: Key to retrieve data for

        Returns:
            Cached data or None if not found
        """
        return self.cache.get(cache_key)

    def delete(self, cache_key: str) -> None:
        """Delete cached data by key.

        Args:
            cache_key: Key to delete
        """
        self.cache.delete(cache_key)

    def clear(self, task_id=None) -> None:
        """Clear all cached data."""
        self.initiate_task(task_id, 1)
        try:
            self.cache.clear()
            self.report_task(1)
            self.complete_task()
        except Exception as e:
            self.fail_task(str(e))
            raise
        logger.info("Cache Cleared")

    def get_image_cache_key(self, external_id: str, height: int, width: int) -> str:
        """Generate cache key for an image with specific dimensions.

        Args:
            external_id: External ID of the image
            height: Image height
            width: Image width

        Returns:
            Formatted cache key string
        """
        return f"{external_id}:{settings.SMPL_FRM_IMAGE_FILL_MODE}:{height}:{width}"
