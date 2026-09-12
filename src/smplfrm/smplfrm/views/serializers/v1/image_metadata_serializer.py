"""JSON:API serializer for image metadata resources.

Uses rest_framework_json_api for proper JSON:API document structure.
"""

from rest_framework_json_api import serializers
from rest_framework_json_api.relations import ResourceRelatedField

from smplfrm.models import ImageMetadata


class ExternalIdResourceRelatedField(ResourceRelatedField):
    """ResourceRelatedField that uses external_id instead of pk for relationship IDs.

    Requires queryset to use select_related() for the related field to avoid N+1.
    """

    def use_pk_only_optimization(self):
        """Disable pk-only optimization to access external_id on the related object."""
        return False

    def get_resource_id(self, value):
        """Return external_id as the resource identifier."""
        return value.external_id


class ImageMetadataSerializer(serializers.ModelSerializer):
    """Serializer for image metadata resources.

    Uses external_id as the JSON:API id field.
    Includes relationship to parent image using image's external_id.
    exif field is intentionally excluded.

    Note: Queryset should use select_related('image') for efficient
    relationship serialization.
    """

    id = serializers.CharField(source="external_id", read_only=True)
    image = ExternalIdResourceRelatedField(read_only=True)

    class Meta:
        model = ImageMetadata
        resource_name = "image_metadata"
        fields = [
            "id",
            "taken",
            "created",
            "updated",
            "image",
        ]
        read_only_fields = ["id", "taken", "created", "updated", "image"]

    included_serializers = {
        "image": "smplfrm.views.serializers.v1.image_serializer.ImageSerializer",
    }

    class JSONAPIMeta:
        included_resources = []
