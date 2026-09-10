"""JSON:API serializer for task resources.

Uses rest_framework_json_api with dynamic type based on task_type.
Each task_type maps to a distinct JSON:API type (e.g., rescan_library_tasks).
"""

from rest_framework_json_api import serializers

from smplfrm.models import Task

# Map task_type values to JSON:API type names (snake_case with _tasks suffix)
TASK_TYPE_TO_JSONAPI_TYPE = {
    Task.TaskType.RESCAN_LIBRARY: "rescan_library_tasks",
    Task.TaskType.RESET_IMAGE_COUNT: "reset_image_count_tasks",
    Task.TaskType.CLEAR_CACHE: "clear_cache_tasks",
}

# Reverse mapping for parsing incoming requests
JSONAPI_TYPE_TO_TASK_TYPE = {v: k for k, v in TASK_TYPE_TO_JSONAPI_TYPE.items()}


class TaskSerializer(serializers.ModelSerializer):
    """Serializer for task resources.

    Uses external_id as the JSON:API id field.
    The JSON:API type is dynamically derived from task_type.
    """

    id = serializers.CharField(source="external_id", read_only=True)
    label = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "label",
            "status",
            "progress",
            "error",
            "created",
        ]
        read_only_fields = ["id", "label", "status", "progress", "error", "created"]

    def get_label(self, obj):
        """Return human-readable label for the task type."""
        return obj.get_task_type_display()

    @classmethod
    def get_resource_type_from_instance(cls, instance):
        """Return JSON:API type based on task_type.

        This is called by JsonApiRenderer.build_json_resource_obj to
        determine the type field dynamically per instance.
        """
        return TASK_TYPE_TO_JSONAPI_TYPE.get(instance.task_type, "tasks")

    @classmethod
    def get_accepted_types(cls):
        """Return list of accepted JSON:API types for this serializer.

        This is called by JsonApiParser to validate incoming request types.
        """
        return list(TASK_TYPE_TO_JSONAPI_TYPE.values())

    class JSONAPIMeta:
        resource_name = "tasks"
