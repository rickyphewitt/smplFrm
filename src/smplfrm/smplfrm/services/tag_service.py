from typing import Any, Dict, Optional

from django.db.models import Count, Q, QuerySet

from smplfrm.models import Tag
from smplfrm.services.library.canonicalize import canonicalize

from .base_service import BaseService


class TagService(BaseService):
    """Read-only service for tags.

    Tags are created and revived only by the library scan
    (ImageTagService.sync), so create, update, delete, and destroy are not
    supported here.
    """

    def create(self, data: Dict[str, Any]) -> Tag:
        raise NotImplementedError("Tags are created by the library scan")

    def read(self, ext_id: str, deleted: bool = False) -> Tag:
        """Retrieve a tag by external ID.

        Args:
            ext_id: External identifier
            deleted: Whether to include soft-deleted records

        Returns:
            Tag instance
        """
        return Tag.objects.get(external_id=ext_id, deleted=deleted)

    def list(self, **kwargs) -> QuerySet[Tag]:
        """List tags with optional filtering.

        Args:
            **kwargs: Filter parameters

        Returns:
            QuerySet of Tag instances
        """
        if kwargs:
            return Tag.objects.filter(**kwargs)
        return Tag.objects.all()

    def list_with_usage(self, value: Optional[str] = None) -> QuerySet[Tag]:
        """List non-deleted tags annotated with usage_count, ordered by value.

        usage_count is the number of non-deleted images linked to the tag.
        It is computed in the same query to avoid one count per tag.

        Args:
            value: Optional tag text; canonicalized, then matched exactly

        Returns:
            QuerySet of Tag instances with a usage_count attribute
        """
        queryset = Tag.objects.filter(deleted=False)
        if value is not None:
            canonical = canonicalize(value)
            if canonical is None:
                return queryset.none()
            queryset = queryset.filter(value=canonical)
        return queryset.annotate(
            usage_count=Count("image_tags", filter=Q(image_tags__image__deleted=False))
        ).order_by("value")

    def update(self, entity: Tag) -> Tag:
        raise NotImplementedError("Tags are updated by the library scan")

    def delete(self, ext_id: str) -> None:
        raise NotImplementedError("Tags cannot be deleted")

    def destroy(self, ext_id: str) -> None:
        raise NotImplementedError("Tags cannot be deleted")
