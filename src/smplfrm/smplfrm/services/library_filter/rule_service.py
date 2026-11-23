import logging
from typing import Any, Dict, Optional

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone

from smplfrm.models import LibraryFilter, LibraryFilterRule, Tag
from smplfrm.services.base_service import BaseService

from .exceptions import (
    DuplicateRule,
    LibraryFilterImmutable,
    LibraryFilterNotFound,
    LibraryFilterRequired,
    TagNotFound,
    TagRequired,
    UnknownRuleType,
)
from .rule_handlers import RULE_TYPE_HANDLERS

logger = logging.getLogger(__name__)


class LibraryFilterRuleService(BaseService):
    """Service for library filter rules.

    Invariants kept here:
    - A rule belongs to one live filter for its whole life.
    - A filter has at most one live tag rule per tag.
    - Removing the last live rule of the active filter deactivates it.
    """

    def create(self, data: Dict[str, Any]) -> LibraryFilterRule:
        """Create a rule.

        Args:
            data: ``rule_type``, ``library_filter_id`` (external id), and the
                type's fields (``tag_id`` external id for tag rules)

        Returns:
            Created LibraryFilterRule

        Raises:
            UnknownRuleType, LibraryFilterRequired, LibraryFilterNotFound,
            TagRequired, TagNotFound, DuplicateRule
        """
        rule_type = data.get("rule_type")
        if rule_type not in RULE_TYPE_HANDLERS:
            raise UnknownRuleType()
        library_filter = self._live_filter(data.get("library_filter_id"))
        tag = self._live_tag(data.get("tag_id"))
        if self._tag_in_use(library_filter, tag):
            raise DuplicateRule()
        try:
            with transaction.atomic():
                return LibraryFilterRule.objects.create(
                    library_filter=library_filter, rule_type=rule_type, tag=tag
                )
        except IntegrityError:
            # A concurrent request added the same tag after the pre-check.
            raise DuplicateRule()

    def read(self, ext_id: str, deleted: bool = False) -> LibraryFilterRule:
        """Retrieve a rule by external ID.

        Args:
            ext_id: External identifier
            deleted: Whether to include soft-deleted records

        Returns:
            LibraryFilterRule instance
        """
        return LibraryFilterRule.objects.get(external_id=ext_id, deleted=deleted)

    def list(self, **kwargs) -> QuerySet[LibraryFilterRule]:
        """List rules with optional filtering.

        Args:
            **kwargs: Filter parameters

        Returns:
            QuerySet of LibraryFilterRule instances
        """
        if kwargs:
            return LibraryFilterRule.objects.filter(**kwargs)
        return LibraryFilterRule.objects.all()

    def list_for_api(
        self,
        library_filter_id: Optional[str] = None,
        rule_type: Optional[str] = None,
    ) -> QuerySet[LibraryFilterRule]:
        """List live rules in creation order with their relations loaded.

        Args:
            library_filter_id: Optional parent filter external id
            rule_type: Optional exact match on rule_type

        Returns:
            QuerySet of LibraryFilterRule instances
        """
        queryset = LibraryFilterRule.objects.filter(deleted=False)
        if library_filter_id is not None:
            queryset = queryset.filter(library_filter__external_id=library_filter_id)
        if rule_type is not None:
            queryset = queryset.filter(rule_type=rule_type)
        return queryset.select_related("library_filter", "tag").order_by(
            "created", "id"
        )

    def update(self, entity: LibraryFilterRule) -> LibraryFilterRule:
        """Persist a rule as-is.

        Args:
            entity: LibraryFilterRule to save

        Returns:
            The saved LibraryFilterRule
        """
        entity.save()
        return entity

    def replace(
        self, rule: LibraryFilterRule, data: Dict[str, Any]
    ) -> LibraryFilterRule:
        """Replace a rule's references (full update).

        The parent filter must be sent and must not change. The tag may change.

        Args:
            rule: Rule to replace
            data: ``library_filter_id`` and ``tag_id`` (external ids)

        Returns:
            The updated LibraryFilterRule

        Raises:
            LibraryFilterRequired, LibraryFilterImmutable, TagRequired,
            TagNotFound, DuplicateRule
        """
        library_filter_id = data.get("library_filter_id")
        if not library_filter_id:
            raise LibraryFilterRequired()
        if library_filter_id != rule.library_filter.external_id:
            raise LibraryFilterImmutable()
        tag = self._live_tag(data.get("tag_id"))
        if self._tag_in_use(rule.library_filter, tag, exclude_pk=rule.pk):
            raise DuplicateRule()

        rule.tag = tag
        try:
            with transaction.atomic():
                rule.save()
        except IntegrityError:
            raise DuplicateRule()
        return rule

    def delete(self, ext_id: str) -> None:
        """Soft delete a rule; deactivate its filter if no live rules remain.

        Args:
            ext_id: External identifier
        """
        try:
            rule = LibraryFilterRule.objects.get(external_id=ext_id, deleted=False)
        except LibraryFilterRule.DoesNotExist:
            return
        with transaction.atomic():
            rule.deleted = True
            rule.save()
            self._deactivate_if_empty(rule.library_filter_id)

    def destroy(self, ext_id: str) -> None:
        """Permanently delete a rule; deactivate its filter if no live rules remain.

        Args:
            ext_id: External identifier
        """
        rule = LibraryFilterRule.objects.filter(external_id=ext_id).first()
        if rule is None:
            return
        with transaction.atomic():
            library_filter_id = rule.library_filter_id
            rule.delete()
            self._deactivate_if_empty(library_filter_id)

    @staticmethod
    def _deactivate_if_empty(library_filter_pk: int) -> None:
        has_rules = LibraryFilterRule.objects.filter(
            library_filter_id=library_filter_pk, deleted=False
        ).exists()
        if has_rules:
            return
        deactivated = LibraryFilter.objects.filter(
            pk=library_filter_pk, is_active=True
        ).update(is_active=False, updated=timezone.now())
        if deactivated:
            logger.info("Deactivated library filter after its last rule was removed")

    @staticmethod
    def _live_filter(ext_id: Optional[str]) -> LibraryFilter:
        if not ext_id:
            raise LibraryFilterRequired()
        try:
            return LibraryFilter.objects.get(external_id=ext_id, deleted=False)
        except LibraryFilter.DoesNotExist:
            raise LibraryFilterNotFound()

    @staticmethod
    def _live_tag(ext_id: Optional[str]) -> Tag:
        if not ext_id:
            raise TagRequired()
        try:
            return Tag.objects.get(external_id=ext_id, deleted=False)
        except Tag.DoesNotExist:
            raise TagNotFound()

    @staticmethod
    def _tag_in_use(
        library_filter: LibraryFilter, tag: Tag, exclude_pk: Optional[int] = None
    ) -> bool:
        in_use = LibraryFilterRule.objects.filter(
            library_filter=library_filter,
            rule_type=LibraryFilterRule.RuleType.TAG,
            tag=tag,
            deleted=False,
        )
        if exclude_pk is not None:
            in_use = in_use.exclude(pk=exclude_pk)
        return in_use.exists()
