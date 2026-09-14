"""JSON:API serializer for preload_image_cache_tasks resources.

Validates type-specific attributes for cache preloading:
- image_ids: list of external IDs to preload (max 5 unique)
- width, height: viewport dimensions (1-4096)
"""

from rest_framework import serializers

from smplfrm.services.image_manipulation_service import ImageManipulationService
from smplfrm.views.serializers.v1.task_serializer import TaskSerializer


class PreloadImageCacheTaskSerializer(serializers.Serializer):
    """Serializer for preload_image_cache_tasks creation requests.

    Validates preload-specific input before task creation.
    Does not inherit from TaskSerializer since it handles creation payload,
    not the task resource itself.
    """

    image_ids = serializers.ListField(
        child=serializers.CharField(max_length=16, allow_blank=False),
        allow_empty=False,
        # Note: max_length not set here; post-dedup validation enforces 5 unique IDs
    )
    width = serializers.IntegerField(min_value=1, max_value=4096)
    height = serializers.IntegerField(min_value=1, max_value=4096)

    def validate_image_ids(self, value):
        """Deduplicate and validate image IDs."""
        # Preserve order while deduplicating
        seen = set()
        unique_ids = []
        for image_id in value:
            if image_id not in seen:
                seen.add(image_id)
                unique_ids.append(image_id)

        if len(unique_ids) > 5:
            raise serializers.ValidationError("Maximum 5 unique image IDs allowed")

        if len(unique_ids) == 0:
            raise serializers.ValidationError("At least one image ID required")

        return unique_ids

    def validate(self, attrs):
        """Cross-field validation using ImageManipulationService."""
        width = attrs.get("width")
        height = attrs.get("height")

        # Validate dimensions using the service's validation logic
        result = ImageManipulationService.validate_dimensions(str(width), str(height))
        if result[0] is None:
            raise serializers.ValidationError({"dimensions": result[1]})

        return attrs
