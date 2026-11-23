"""JSON:API serializer for library filter resources."""

from rest_framework.relations import ManyRelatedField
from rest_framework_json_api import serializers

from smplfrm.models import LibraryFilter, LibraryFilterRule
from smplfrm.services.library_filter.rule_handlers import RULE_TYPE_TO_JSONAPI_TYPE
from smplfrm.views.serializers.v1.image_metadata_serializer import (
    ExternalIdResourceRelatedField,
)


class RuleIdentifierField(ExternalIdResourceRelatedField):
    """Rule identifier whose ``type`` is the rule's own JSON:API type."""

    def to_representation(self, value):
        return {
            "type": RULE_TYPE_TO_JSONAPI_TYPE[value.rule_type],
            "id": value.external_id,
        }


class LiveRulesField(ManyRelatedField):
    """Read-only list of a filter's non-deleted rules.

    Filtering happens in Python so a ``rules`` prefetch on the queryset is
    reused instead of issuing one query per filter.
    """

    def get_attribute(self, instance):
        return [rule for rule in instance.rules.all() if not rule.deleted]


class LibraryFilterSerializer(serializers.ModelSerializer):
    """Serializer for library filters.

    ``rules`` is read-only; rules are managed through their own resource.
    Name uniqueness and the single-active-filter rule are enforced by
    LibraryFilterService, so model-derived uniqueness validators are removed.
    """

    id = serializers.CharField(source="external_id", read_only=True)
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    is_active = serializers.BooleanField(required=False)
    rules = LiveRulesField(
        child_relation=RuleIdentifierField(read_only=True, model=LibraryFilterRule),
        read_only=True,
    )

    class Meta:
        model = LibraryFilter
        resource_name = "library_filters"
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "created",
            "updated",
            "rules",
        ]
        read_only_fields = ["id", "created", "updated", "rules"]
        validators = []
