"""JSON:API serializer for tag rules (``tag_library_filter_rules``)."""

from typing import Any, Dict

from rest_framework_json_api import serializers

from smplfrm.models import LibraryFilterRule
from smplfrm.services.library_filter.rule_handlers import RULE_TYPE_TO_JSONAPI_TYPE
from smplfrm.views.serializers.v1.image_metadata_serializer import (
    ExternalIdResourceRelatedField,
)

from .relationships import relationship_id


class TagLibraryFilterRuleSerializer(serializers.ModelSerializer):
    """Serializer for rules that match images carrying one tag.

    The tag is exposed only as a relationship; the tag text itself is never an
    attribute of the rule. Queryset should select_related('library_filter',
    'tag') because both relationships render external ids.
    """

    id = serializers.CharField(source="external_id", read_only=True)
    library_filter = ExternalIdResourceRelatedField(read_only=True)
    tag = ExternalIdResourceRelatedField(read_only=True)

    included_serializers = {
        "library_filter": (
            "smplfrm.views.serializers.v1.library_filter_serializer.LibraryFilterSerializer"
        ),
        "tag": "smplfrm.views.serializers.v1.tag_serializer.TagSerializer",
    }

    class Meta:
        model = LibraryFilterRule
        fields = ["id", "created", "updated", "library_filter", "tag"]
        read_only_fields = fields

    class JSONAPIMeta:
        resource_name = "library_filter_rules"
        included_resources = []

    @classmethod
    def get_resource_type_from_instance(cls, instance):
        """Return the rule's JSON:API type, derived from its rule_type."""
        return RULE_TYPE_TO_JSONAPI_TYPE[instance.rule_type]

    @classmethod
    def to_service_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map a parsed request document to LibraryFilterRuleService input.

        Missing relationships map to None; the service reports them with
        their stable error codes.
        """
        return {
            "library_filter_id": relationship_id(data, "library_filter"),
            "tag_id": relationship_id(data, "tag"),
        }
