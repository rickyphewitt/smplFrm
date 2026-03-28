from rest_framework import serializers

from smplfrm.models import Config


class ConfigSerializer(serializers.HyperlinkedModelSerializer):

    id = serializers.CharField(source="external_id", read_only=True)

    class Meta:
        model = Config
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
        ]
