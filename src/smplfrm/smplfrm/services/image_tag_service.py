import logging
from typing import Any, Dict, Iterable

from django.db import transaction
from django.db.models import QuerySet

from smplfrm.models import Image, ImageTag, Tag
from smplfrm.services.library.tag_extractor import ExtractedTag

from .base_service import BaseService

logger = logging.getLogger(__name__)


class ImageTagService(BaseService):
    """Service for the links between images and their embedded tags."""

    def create(self, data: Dict[str, Any]) -> ImageTag:
        """Create an image-tag link.

        Args:
            data: Dictionary of ImageTag attributes

        Returns:
            Created ImageTag instance
        """
        return ImageTag.objects.create(**data)

    def read(self, ext_id: str, deleted: bool = False) -> ImageTag:
        """Retrieve an image-tag link by external ID.

        Args:
            ext_id: External identifier
            deleted: Whether to include soft-deleted records

        Returns:
            ImageTag instance
        """
        return ImageTag.objects.get(external_id=ext_id, deleted=deleted)

    def list(self, **kwargs) -> QuerySet[ImageTag]:
        """List image-tag links with optional filtering.

        Args:
            **kwargs: Filter parameters

        Returns:
            QuerySet of ImageTag instances
        """
        if kwargs:
            return ImageTag.objects.filter(**kwargs)
        return ImageTag.objects.all()

    def update(self, image_tag: ImageTag) -> ImageTag:
        """Persist changes to an image-tag link.

        Args:
            image_tag: ImageTag instance to update

        Returns:
            Updated ImageTag instance
        """
        image_tag.save()
        return image_tag

    def delete(self, ext_id: str) -> None:
        """Soft delete an image-tag link by external ID.

        Args:
            ext_id: External identifier
        """
        try:
            image_tag = ImageTag.objects.get(external_id=ext_id, deleted=False)
        except ImageTag.DoesNotExist:
            return
        image_tag.deleted = True
        image_tag.save()

    def destroy(self, ext_id: str) -> None:
        """Permanently delete an image-tag link by external ID.

        Args:
            ext_id: External identifier
        """
        ImageTag.objects.filter(external_id=ext_id).delete()

    @transaction.atomic
    def sync(self, image: Image, extracted: Iterable[ExtractedTag]) -> None:
        """Make an image's tag links match the tags just read from its file.

        Creates missing Tag rows, creates or updates the image's links, and
        removes links for tags the file no longer carries. Tag rows are never
        deleted here, even when no image uses them any more.

        Args:
            image: Image the tags were read from
            extracted: Tags returned by TagExtractor.extract()
        """
        extracted = list(extracted)
        tags_by_value = {e.canonical: self._upsert_tag(e) for e in extracted}

        existing = {
            link.tag.value: link
            for link in ImageTag.objects.filter(image=image).select_related("tag")
        }

        for e in extracted:
            sources = sorted(set(e.sources))
            hierarchy = list(e.raw_hierarchy)
            link = existing.get(e.canonical)
            if link is None:
                ImageTag.objects.create(
                    image=image,
                    tag=tags_by_value[e.canonical],
                    sources=sources,
                    raw_hierarchy=hierarchy,
                )
                continue
            if (
                link.sources != sources
                or link.raw_hierarchy != hierarchy
                or link.deleted
            ):
                link.sources = sources
                link.raw_hierarchy = hierarchy
                link.deleted = False
                link.save()

        stale_ids = [
            link.id for value, link in existing.items() if value not in tags_by_value
        ]
        if stale_ids:
            ImageTag.objects.filter(id__in=stale_ids).delete()
            logger.debug(
                "Removed %d stale tag link(s) from image %s",
                len(stale_ids),
                image.external_id,
            )

    @staticmethod
    def _upsert_tag(e: ExtractedTag) -> Tag:
        tag, created = Tag.objects.get_or_create(
            value=e.canonical, defaults={"display_value": e.display}
        )
        if created:
            return tag
        update_fields = []
        if tag.deleted:
            # A tag seen again on disk is live again.
            tag.deleted = False
            update_fields.append("deleted")
        if not tag.display_value:
            tag.display_value = e.display
            update_fields.append("display_value")
        if update_fields:
            update_fields.append("updated")
            tag.save(update_fields=update_fields)
        return tag
