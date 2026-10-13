"""JSON:API serializer for config resources.

Uses rest_framework_json_api for proper JSON:API document structure.
"""

from rest_framework_json_api import serializers

from smplfrm.models import Config
from smplfrm.themes import get_theme_map


class ConfigSerializer(serializers.ModelSerializer):
    """Serializer for config resources.

    Uses external_id as the JSON:API id field.
    is_active is writable; the service layer controls activation logic
    and handles the unique constraint (only one active config).
    """

    id = serializers.CharField(source="external_id", read_only=True)
    # Override is_active to remove the unique validator - service handles this
    is_active = serializers.BooleanField(required=False)

    class Meta:
        model = Config
        resource_name = "configs"
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "display_date",
            "display_clock",
            "image_refresh_interval",
            "image_transition_interval",
            "image_zoom_effect",
            "image_transition_type",
            "image_cache_timeout",
            "image_fill_mode",
            "force_date_from_path",
            "timezone",
            "plugins",
            "theme",
        ]
        read_only_fields = ["id"]

    def validate_theme(self, value):
        """Reject a theme id that is not in the registry.

        Validation lives here rather than as a model-level `choices`
        constraint so adding a theme never needs a migration.
        """
        if value not in get_theme_map():
            raise serializers.ValidationError(f"'{value}' is not a registered theme.")
        return value
