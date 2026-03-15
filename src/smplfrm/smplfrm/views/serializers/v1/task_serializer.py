from rest_framework import serializers

from smplfrm.models import Task


class TaskSerializer(serializers.HyperlinkedModelSerializer):

    id = serializers.CharField(source="external_id", read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "task_type",
            "status",
            "progress",
            "error",
        ]
        read_only_fields = ["id", "status", "progress", "error"]
