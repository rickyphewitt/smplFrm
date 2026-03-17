from rest_framework import serializers

from smplfrm.models import Task


class TaskSerializer(serializers.HyperlinkedModelSerializer):

    id = serializers.CharField(source="external_id", read_only=True)
    task_type_label = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "task_type",
            "task_type_label",
            "status",
            "progress",
            "error",
            "created",
        ]
        read_only_fields = ["id", "status", "progress", "error", "created"]

    def get_task_type_label(self, obj):
        return obj.get_task_type_display()
