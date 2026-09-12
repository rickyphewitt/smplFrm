"""JSON:API serializer for image resources.

Uses rest_framework_json_api for proper JSON:API document structure.
"""

from rest_framework_json_api import serializers

from smplfrm.models import Image


class ImageSerializer(serializers.ModelSerializer):
    """Serializer for image resources.

    Uses external_id as the JSON:API id field.
    file_path is intentionally excluded for security.
    """

    id = serializers.CharField(source="external_id", read_only=True)

    class Meta:
        model = Image
        resource_name = "images"
        fields = [
            "id",
            "name",
            "file_name",
            "created",
            "updated",
            "view_count",
        ]
        read_only_fields = [
            "id",
            "name",
            "file_name",
            "created",
            "updated",
            "view_count",
        ]
