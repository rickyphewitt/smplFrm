"""JSON:API serializer for the library filter settings resource."""

from rest_framework_json_api import serializers

from smplfrm.models import LibraryFilterSettings


class LibraryFilterSettingsSerializer(serializers.ModelSerializer):
    """Serializer for the single settings row. Only ``enabled`` is writable."""

    id = serializers.CharField(source="external_id", read_only=True)
    enabled = serializers.BooleanField(required=True)

    class Meta:
        model = LibraryFilterSettings
        resource_name = "library_filter_settings"
        fields = ["id", "enabled", "created", "updated"]
        read_only_fields = ["id", "created", "updated"]
