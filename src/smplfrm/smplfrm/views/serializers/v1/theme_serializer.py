"""JSON:API serializer for theme resources.

Themes have no database row, so this is a non-model serializer with an
explicit resource_name and get_id(), following the pattern already
established by the Spotify plugin's serializers
(views/api/plugins/v1/spotify/serializers.py).
"""

from rest_framework_json_api import serializers


class ThemeSerializer(serializers.Serializer):
    """Serializer for themes resources.

    `stylesheet` is deliberately not a field here: it is server-side detail
    the template resolves directly, and keeping it out of the payload means
    no static path is ever serialized to a client.
    """

    id = serializers.SerializerMethodField()
    label = serializers.CharField()
    description = serializers.CharField()

    class Meta:
        resource_name = "themes"

    def get_id(self, obj):
        return obj.id
