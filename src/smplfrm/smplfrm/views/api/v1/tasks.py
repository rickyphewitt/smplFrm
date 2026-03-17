import logging

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from rest_framework import viewsets, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from smplfrm.models import Task
from smplfrm.services.task_service import TaskService
from smplfrm.views.serializers.v1.task_serializer import TaskSerializer

logger = logging.getLogger(__name__)

TASK_DISPATCH = {
    Task.TaskType.RESCAN_LIBRARY: "scan_library",
    Task.TaskType.RESET_IMAGE_COUNT: "reset_image_count",
    Task.TaskType.CLEAR_CACHE: "clear_cache",
}


class TaskPagination(PageNumberPagination):
    page_size = 5


class TaskViewSet(viewsets.ModelViewSet):

    queryset = Task.objects.filter(deleted=False).order_by("-created")
    serializer_class = TaskSerializer
    pagination_class = TaskPagination
    lookup_field = "external_id"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = TaskService()

    def create(self, request, *args, **kwargs):
        """Create a new task and dispatch to Celery."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task_type = serializer.validated_data["task_type"]
        try:
            task = self.service.create({"task_type": task_type})
        except IntegrityError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_409_CONFLICT,
            )

        from smplfrm.celery import app

        celery_task_name = TASK_DISPATCH.get(task_type)
        if celery_task_name:
            app.send_task(celery_task_name, kwargs={"task_id": task.external_id})

        return Response(
            TaskSerializer(task, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        """Poll task status by external_id."""
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        raise PermissionDenied()

    def partial_update(self, request, *args, **kwargs):
        raise PermissionDenied()

    def destroy(self, request, *args, **kwargs):
        """Soft-delete a task. Running tasks will self-cancel on next progress check."""
        task = self.get_object()
        task.deleted = True
        task.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
