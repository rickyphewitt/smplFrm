import logging
from typing import Any, Dict, List, Optional

from django.db import IntegrityError, transaction
from django.db.models import Prefetch, QuerySet
from django.utils import timezone

from smplfrm.models import LibraryFilter, LibraryFilterRule
from smplfrm.services.base_service import BaseService

from .exceptions import RuleRequired, UniqueName

logger = logging.getLogger(__name__)


class LibraryFilterService(BaseService):
    """Service for library filters.

    Invariants kept here:
    - At most one filter is active; activating one deactivates the others.
    - A filter needs at least one live rule to be active.
    - Live filter names are unique.
    - Deleting a filter deactivates it and soft-deletes its rules.
    """

    def create(self, data: Dict[str, Any]) -> LibraryFilter:
        """Create a library filter.

        Args:
            data: ``name`` (required), ``description``, ``is_active``

        Returns:
            Created LibraryFilter

        Raises:
            RuleRequired: is_active is true; a new filter has no rules yet
            UniqueName: another live filter has this name
        """
        if data.get("is_active", False):
            raise RuleRequired()
        name = data["name"]
        self._ensure_name_free(name)
        try:
            with transaction.atomic():
                return LibraryFilter.objects.create(
                    name=name,
                    description=data.get("description", ""),
                    is_active=False,
                )
        except IntegrityError:
            # A concurrent request took the name after the pre-check.
            raise UniqueName()

    def read(self, ext_id: str, deleted: bool = False) -> LibraryFilter:
        """Retrieve a library filter by external ID.

        Args:
            ext_id: External identifier
            deleted: Whether to include soft-deleted records

        Returns:
            LibraryFilter instance
        """
        return LibraryFilter.objects.get(external_id=ext_id, deleted=deleted)

    def list(self, **kwargs) -> QuerySet[LibraryFilter]:
        """List library filters with optional filtering.

        Args:
            **kwargs: Filter parameters

        Returns:
            QuerySet of LibraryFilter instances
        """
        if kwargs:
            return LibraryFilter.objects.filter(**kwargs)
        return LibraryFilter.objects.all()

    def list_for_api(self, is_active: Optional[bool] = None) -> QuerySet[LibraryFilter]:
        """List live filters ordered by name, with their live rules prefetched.

        Args:
            is_active: Optional exact match on is_active

        Returns:
            QuerySet of LibraryFilter instances
        """
        queryset = LibraryFilter.objects.filter(deleted=False)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        live_rules = LibraryFilterRule.objects.filter(deleted=False).order_by("id")
        return queryset.prefetch_related(
            Prefetch("rules", queryset=live_rules)
        ).order_by("name", "id")

    def update(self, entity: LibraryFilter) -> LibraryFilter:
        """Persist a library filter as-is.

        Args:
            entity: LibraryFilter to save

        Returns:
            The saved LibraryFilter
        """
        entity.save()
        return entity

    def replace(
        self, library_filter: LibraryFilter, data: Dict[str, Any]
    ) -> LibraryFilter:
        """Replace a filter's attributes (full update).

        Omitted ``description`` becomes "" and omitted ``is_active`` becomes
        false. Activating deactivates any other active filter in the same
        transaction.

        Args:
            library_filter: Filter to replace
            data: ``name`` (required), ``description``, ``is_active``

        Returns:
            The updated LibraryFilter

        Raises:
            RuleRequired: is_active is true and the filter has no live rules
            UniqueName: another live filter has this name
        """
        name = data["name"]
        is_active = data.get("is_active", False)
        self._ensure_name_free(name, exclude_pk=library_filter.pk)
        if is_active and not self.has_live_rules(library_filter):
            raise RuleRequired()

        with transaction.atomic():
            if is_active:
                self._deactivate_others(library_filter)
            library_filter.name = name
            library_filter.description = data.get("description", "")
            library_filter.is_active = is_active
            try:
                with transaction.atomic():
                    library_filter.save()
            except IntegrityError:
                raise UniqueName()
        return library_filter

    def activate(self, ext_id: str) -> LibraryFilter:
        """Make a filter the active one.

        Args:
            ext_id: External identifier of a live filter

        Returns:
            The activated LibraryFilter

        Raises:
            LibraryFilter.DoesNotExist: no live filter has this id
            RuleRequired: the filter has no live rules
        """
        library_filter = self.read(ext_id)
        if not self.has_live_rules(library_filter):
            raise RuleRequired()
        with transaction.atomic():
            self._deactivate_others(library_filter)
            library_filter.is_active = True
            library_filter.save()
        return library_filter

    def delete(self, ext_id: str) -> None:
        """Soft delete a filter and its rules; an active filter is deactivated.

        Args:
            ext_id: External identifier
        """
        try:
            library_filter = LibraryFilter.objects.get(
                external_id=ext_id, deleted=False
            )
        except LibraryFilter.DoesNotExist:
            return

        with transaction.atomic():
            LibraryFilterRule.objects.filter(
                library_filter=library_filter, deleted=False
            ).update(deleted=True, updated=timezone.now())
            library_filter.is_active = False
            library_filter.deleted = True
            library_filter.save()
        logger.info("Deleted library filter %s", library_filter.external_id)

    def destroy(self, ext_id: str) -> None:
        """Permanently delete a filter and its rules.

        Args:
            ext_id: External identifier
        """
        LibraryFilter.objects.filter(external_id=ext_id).delete()

    def has_live_rules(self, library_filter: LibraryFilter) -> bool:
        """Return whether the filter has at least one non-deleted rule."""
        return LibraryFilterRule.objects.filter(
            library_filter=library_filter, deleted=False
        ).exists()

    def active_rules(self) -> List[LibraryFilterRule]:
        """Return the live rules of the live active filter, in one query.

        Rule relations are loaded with the rules, so callers can read them
        without further queries. Empty when no filter is active.
        """
        return list(
            LibraryFilterRule.objects.filter(
                deleted=False,
                library_filter__is_active=True,
                library_filter__deleted=False,
            )
            .select_related("tag")
            .order_by("id")
        )

    @staticmethod
    def _deactivate_others(library_filter: LibraryFilter) -> None:
        LibraryFilter.objects.filter(is_active=True).exclude(
            pk=library_filter.pk
        ).update(is_active=False, updated=timezone.now())

    @staticmethod
    def _ensure_name_free(name: str, exclude_pk: Optional[int] = None) -> None:
        taken = LibraryFilter.objects.filter(name=name, deleted=False)
        if exclude_pk is not None:
            taken = taken.exclude(pk=exclude_pk)
        if taken.exists():
            raise UniqueName()
