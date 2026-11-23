import logging
import operator
from functools import reduce
from typing import Any, Dict, Optional
from django.db.models import QuerySet

from smplfrm.models import Image

from .base_service import BaseService

from smplfrm.services.task_reporting_service import TaskReportingService
from smplfrm.models.task import TaskType

logger = logging.getLogger(__name__)


# Curated sort profiles map profile keys to complete ordering tuples
SORT_PROFILES = {
    "display_priority": ("view_count", "-created", "external_id"),
}


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

    def read(
        self,
        ext_id: str,
        deleted: bool = False,
        *,
        enforce_visibility: bool = True,
    ) -> Image:
        """Retrieve an image by external ID.

        Args:
            ext_id: External identifier
            deleted: Whether to look up a soft-deleted record instead of a live one
            enforce_visibility: Hide images outside the active library filter.
                Pass False only for library maintenance, never for serving.

        Returns:
            Image instance

        Raises:
            Image.DoesNotExist: no matching image, or it is hidden by the filter
        """
        if enforce_visibility:
            queryset = self.visible_queryset(include_deleted=deleted)
        else:
            queryset = Image.objects.all()
        return queryset.get(external_id=ext_id, deleted=deleted)

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

    def visible_queryset(self, include_deleted: bool = False) -> QuerySet[Image]:
        """Return the images that may be served, per the library filter.

        This is the single place that decides which images are displayable.
        Every path that serves images (API, frame, cache, preload) reads
        through it.

        - Filtering off: every image (live images only unless include_deleted).
        - Filtering on, no active filter, or no usable rules: no images.
        - Filtering on with an active filter: images matching any of its
          rules. Each rule type's handler supplies the predicate.

        Runs two queries (the settings row and the active rules) before the
        returned queryset is evaluated.

        Args:
            include_deleted: Also return soft-deleted images

        Returns:
            QuerySet of Image instances
        """
        from smplfrm.services.library_filter import (
            LibraryFilterService,
            LibraryFilterSettingsService,
        )
        from smplfrm.services.library_filter.rule_handlers import RULE_TYPE_HANDLERS

        base = (
            Image.objects.all()
            if include_deleted
            else Image.objects.filter(deleted=False)
        )
        if not LibraryFilterSettingsService().get().enabled:
            return base

        predicates = []
        for rule in LibraryFilterService().active_rules():
            handler = RULE_TYPE_HANDLERS.get(rule.rule_type)
            if handler is None:
                # Fail closed: a rule that cannot be applied must not widen
                # the set of displayed images.
                logger.warning(
                    "Library filter rule %s has unknown type; hiding all images",
                    rule.external_id,
                )
                return base.none()
            predicates.append(handler.to_q(rule))

        if not predicates:
            return base.none()

        # A subquery rather than a join keeps one row per image even when an
        # image matches several rules, without needing distinct().
        matching = Image.objects.filter(reduce(operator.or_, predicates)).values("pk")
        return base.filter(pk__in=matching)

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
            return self.visible_queryset().order_by("view_count", "-created")
        except Exception as e:
            logger.error(f"Failed to load next image: {e}")
            return None

    def get_ordered_images(self, sort_profile: Optional[str]) -> QuerySet[Image]:
        """Get images ordered by the specified sort profile.

        Args:
            sort_profile: Curated profile key, or None for default order

        Returns:
            QuerySet of visible Image instances in requested order

        Raises:
            ValueError: If sort_profile is not in SORT_PROFILES
        """
        if sort_profile is None:
            # Default behavior: newest first
            return self.visible_queryset().order_by("-created")

        if sort_profile not in SORT_PROFILES:
            raise ValueError(f"Unknown sort profile: {sort_profile}")

        ordering = SORT_PROFILES[sort_profile]
        return self.visible_queryset().order_by(*ordering)

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
            self.fail_task("Image count reset operation failed", exception=e)
            raise
        logger.info("Image Count Reset")
