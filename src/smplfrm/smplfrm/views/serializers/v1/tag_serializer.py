"""JSON:API serializer for tag resources."""

from rest_framework_json_api import serializers

from smplfrm.models import Tag


class TagSerializer(serializers.ModelSerializer):
    """Read-only serializer for tags.

    usage_count is read from the queryset annotation added by
    TagService.list_with_usage().
    """

    id = serializers.CharField(source="external_id", read_only=True)
    usage_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tag
        resource_name = "tags"
        fields = ["id", "value", "display_value", "usage_count", "created", "updated"]
        read_only_fields = fields
