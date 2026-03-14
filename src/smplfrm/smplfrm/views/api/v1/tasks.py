import logging

from django.core.exceptions import PermissionDenied
from rest_framework import viewsets, status
from rest_framework.response import Response

from smplfrm.models import Task
from smplfrm.services.task_service import TaskService
from smplfrm.views.serializers.v1.task_serializer import TaskSerializer

logger = logging.getLogger(__name__)


class TaskViewSet(viewsets.ModelViewSet):

    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    lookup_field = "external_id"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = TaskService()

    def create(self, request, *args, **kwargs):
        """Create a new task. Only task_type is required."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = self.service.create(
            {"task_type": serializer.validated_data["task_type"]}
        )
        return Response(
            TaskSerializer(task, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        """Poll task status by external_id."""
        return super().retrieve(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        raise PermissionDenied()

    def update(self, request, *args, **kwargs):
        raise PermissionDenied()

    def partial_update(self, request, *args, **kwargs):
        raise PermissionDenied()

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied()
