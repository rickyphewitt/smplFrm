"""Task API views.

Provides JSON:API endpoints for task list, detail, create, and delete.
Update and partial update are forbidden.

Task types are expressed as the JSON:API type field:
- rescan_library_tasks
- reset_image_count_tasks
- clear_cache_tasks
"""

import logging

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.http import Http404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework_json_api.pagination import JsonApiPageNumberPagination

from smplfrm.jsonapi import (
    JsonApiRenderer,
    JsonApiParser,
    jsonapi_exception_handler,
)
from smplfrm.models import Task
from smplfrm.services.task_service import TaskService
from smplfrm.throttles import (
    GlobalAnonThrottle,
    GlobalAuthenticatedThrottle,
    GlobalTaskThrottle,
)
from smplfrm.views.serializers.v1.task_serializer import (
    TaskSerializer,
    JSONAPI_TYPE_TO_TASK_TYPE,
    TASK_TYPE_TO_JSONAPI_TYPE,
)

logger = logging.getLogger(__name__)

TASK_DISPATCH = {
    Task.TaskType.RESCAN_LIBRARY: "scan_library",
    Task.TaskType.RESET_IMAGE_COUNT: "reset_image_count",
    Task.TaskType.CLEAR_CACHE: "clear_cache",
}


class TaskPagination(JsonApiPageNumberPagination):
    """JSON:API pagination for tasks with page[number] and page[size]."""

    page_size = 5
    max_page_size = 100


class TaskViewSet(viewsets.ModelViewSet):
    """JSON:API Task endpoint.

    Supports:
    - GET /tasks - list all tasks (paginated)
    - GET /tasks/{external_id} - task detail
    - POST /tasks - create a new task (type determines task_type)
    - DELETE /tasks/{external_id} - soft-delete task

    Forbidden:
    - PUT (update)
    - PATCH (partial update)

    Security:
    - Returns 403 for non-existent resources to prevent enumeration attacks
    """

    queryset = Task.objects.filter(deleted=False).order_by("-created")
    serializer_class = TaskSerializer
    renderer_classes = [JsonApiRenderer]
    parser_classes = [JsonApiParser]
    pagination_class = TaskPagination
    lookup_field = "external_id"
    throttle_classes = [
        GlobalAnonThrottle,
        GlobalAuthenticatedThrottle,
        GlobalTaskThrottle,
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = TaskService()

    def get_exception_handler(self):
        return jsonapi_exception_handler

    def get_object(self):
        """Return 403 instead of 404 to prevent resource enumeration."""
        try:
            return super().get_object()
        except Http404:
            raise PermissionDenied("Access denied")

    def create(self, request, *args, **kwargs):
        """Create a new task and dispatch to Celery.

        The task_type is determined from the JSON:API type field.
        """
        # Extract type from JSON:API document
        # The parser flattens the document, but we need the original type
        jsonapi_type = request.data.get("type")
        if not jsonapi_type:
            return Response(
                {
                    "errors": [
                        {
                            "status": "400",
                            "code": "invalid_type",
                            "detail": "Missing required 'type' field",
                            "source": {"pointer": "/data/type"},
                        }
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        task_type = JSONAPI_TYPE_TO_TASK_TYPE.get(jsonapi_type)
        if not task_type:
            valid_types = ", ".join(sorted(JSONAPI_TYPE_TO_TASK_TYPE.keys()))
            return Response(
                {
                    "errors": [
                        {
                            "status": "400",
                            "code": "invalid_type",
                            "detail": f"Invalid type '{jsonapi_type}'. "
                            f"Valid types: {valid_types}",
                            "source": {"pointer": "/data/type"},
                        }
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            task = self.service.create({"task_type": task_type})
        except IntegrityError as e:
            logger.error("IntegrityError during task creation: %s", e, exc_info=True)
            return Response(
                {
                    "errors": [
                        {
                            "status": "409",
                            "code": "conflict",
                            "detail": "A conflicting task already exists",
                        }
                    ]
                },
                status=status.HTTP_409_CONFLICT,
            )
        except Exception as e:
            logger.error("Unexpected error during task creation: %s", e, exc_info=True)
            return Response(
                {
                    "errors": [
                        {
                            "status": "500",
                            "code": "internal_error",
                            "detail": "An internal error occurred",
                        }
                    ]
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        from smplfrm.celery import app

        celery_task_name = TASK_DISPATCH.get(task_type)
        if celery_task_name:
            app.send_task(celery_task_name, kwargs={"task_id": task.external_id})

        serializer = self.get_serializer(task)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        return Response(
            {
                "errors": [
                    {
                        "status": "405",
                        "code": "method_not_allowed",
                        "detail": "Task update is not supported",
                    }
                ]
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {
                "errors": [
                    {
                        "status": "405",
                        "code": "method_not_allowed",
                        "detail": "Task partial update is not supported",
                    }
                ]
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        """Soft-delete a task. Running tasks will self-cancel on next progress check."""
        task = self.get_object()
        self.service.delete(task.external_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
