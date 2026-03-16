import logging
from typing import Any, Dict, Optional
from django.db.models import QuerySet

from smplfrm.models import Image

from .base_service import BaseService

from smplfrm.services.task_reporting_service import TaskReportingService
from smplfrm.models.task import TaskType

logger = logging.getLogger(__name__)


class ImageService(BaseService, TaskReportingService):
    """Service for managing image records and view tracking."""

    def __init__(self):
        TaskReportingService.__init__(self, task_type=TaskType.RESET_IMAGE_COUNT)

    def create(self, data: Dict[str, Any]) -> Image:
        """Create a new image record.

        Args:
            data: Dictionary containing image attributes

        Returns:
            Created Image instance
        """
        return Image.objects.create(**data)

    def read(self, ext_id: str, deleted: bool = False) -> Image:
        """Retrieve an image by external ID.

        Args:
            ext_id: External identifier
            deleted: Whether to include soft-deleted records

        Returns:
            Image instance
        """
        return Image.objects.get(external_id=ext_id, deleted=deleted)

    def list(self, **kwargs) -> QuerySet[Image]:
        """List images with optional filtering.

        Args:
            **kwargs: Filter parameters

        Returns:
            QuerySet of Image instances
        """
        if kwargs:
            return Image.objects.filter(**kwargs)
        return Image.objects.all()

    def update(self, image: Image) -> Image:
        """Update an existing image record.

        Args:
            image: Image instance to update

        Returns:
            Updated Image instance
        """
        image.save()
        return image

    def delete(self, ext_id: str) -> None:
        """Soft delete an image by external ID.

        Args:
            ext_id: External identifier
        """
        try:
            image_to_soft_delete = Image.objects.get(external_id=ext_id, deleted=False)
        except Image.DoesNotExist:
            return

        image_to_soft_delete.deleted = True
        image_to_soft_delete.save()

    def destroy(self, ext_id: str) -> None:
        """Permanently delete an image from the database.

        Args:
            ext_id: External identifier
        """
        try:
            image_to_destroy = Image.objects.get(external_id=ext_id)
        except Image.DoesNotExist:
            return

        image_to_destroy.delete()

    def read_by_file_name_and_file_path(
        self, file_name: str, file_path: str
    ) -> Optional[Image]:
        """Retrieve an image by file name and path.

        Args:
            file_name: Name of the image file
            file_path: Path to the image file

        Returns:
            Image instance if found, None otherwise
        """
        try:
            return Image.objects.get(file_name=file_name, file_path=file_path)
        except Image.DoesNotExist:
            return None

    def increment_view_count(self, image: Image) -> None:
        """Increment the view count for an image.

        Args:
            image: Image instance to update
        """
        image.view_count = image.view_count + 1
        self.update(image)

    def get_next(self) -> Optional[QuerySet[Image]]:
        """Get images ordered by least viewed and most recently created.

        Returns:
            QuerySet of Image instances ordered by view count and creation date,
            or None if an error occurs
        """
        try:
            return (
                Image.objects.all()
                .filter(deleted=False)
                .order_by("view_count", "-created")
            )
        except Exception as e:
            logger.error(f"Failed to load next image: {e}")
            return None

    def reset_all_view_count(self, task_id=None) -> None:
        """Reset view count for all images."""
        logger.info("Resetting All Image Counts")
        images = list(Image.objects.all())
        self.initiate_task(task_id, len(images))
        try:
            for i, image in enumerate(images):
                image.view_count = 0
                image.save()
                self.report_task(i + 1)
            self.complete_task()
        except Exception as e:
            self.fail_task(str(e))
            raise
        logger.info("Image Count Reset")
