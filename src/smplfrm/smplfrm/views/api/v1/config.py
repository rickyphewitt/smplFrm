"""Config API views.

Provides JSON:API endpoints for config list, detail, create, update, and delete.
Partial update is forbidden.
"""

import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework_json_api.pagination import JsonApiPageNumberPagination

from smplfrm.jsonapi import (
    JsonApiRenderer,
    JsonApiParser,
    jsonapi_exception_handler,
)
from smplfrm.models import Config
from smplfrm.services.config_service import ConfigService, PRESET_PREFIX
from smplfrm.views.serializers.v1.config_serializer import (
    ConfigSerializer,
)

logger = logging.getLogger(__name__)


class ConfigPagination(JsonApiPageNumberPagination):
    """JSON:API pagination for configs with page[number] and page[size]."""

    page_size = 5
    max_page_size = 100


class ConfigViewSet(viewsets.ModelViewSet):
    """JSON:API Config endpoint.

    Supports:
    - GET /configs - list all configs (paginated)
    - GET /configs/{external_id} - config detail
    - POST /configs - create custom config (name generated server-side)
    - PUT /configs/{external_id} - full update (set is_active=true to activate)
    - DELETE /configs/{external_id} - delete custom config

    Forbidden:
    - PATCH (partial update)
    - PUT/DELETE on system-managed configs (smplFrm prefix)

    Security:
    - Returns 403 for non-existent resources to prevent enumeration attacks
    """

    queryset = Config.objects.all()
    serializer_class = ConfigSerializer
    renderer_classes = [JsonApiRenderer]
    parser_classes = [JsonApiParser]
    pagination_class = ConfigPagination
    lookup_field = "external_id"
    resource_name = "configs"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ConfigService()

    def get_exception_handler(self):
        return jsonapi_exception_handler

    def get_object(self):
        """Return 403 instead of 404 to prevent resource enumeration."""
        try:
            return super().get_object()
        except Http404:
            raise PermissionDenied("Access denied")

    def create(self, request, *args, **kwargs):
        """Create a new custom config.

        Name is always generated server-side as custom-{timestamp}.
        If is_active=true, deactivates the current active config.
        """
        # JSON:API parser flattens data.attributes into request.data
        data = dict(request.data)
        # Remove fields that shouldn't be in create data
        data.pop("id", None)
        data.pop("type", None)

        try:
            config = self.service.create(data)
        except ValueError as e:
            logger.error("Config create error: %s", e, exc_info=True)
            return Response(
                {
                    "errors": [
                        {
                            "status": "400",
                            "code": "validation_error",
                            "detail": str(e),
                        }
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(config)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        config = self.get_object()

        serializer = self.get_serializer(config, data=request.data)
        serializer.is_valid(raise_exception=True)

        # Delegate to service - handles system-managed vs custom logic
        updated_config = self.service.update(config, serializer.validated_data)

        return Response(self.get_serializer(updated_config).data)

    def list(self, request, *args, **kwargs):
        queryset = self.service.list()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        raise PermissionDenied(
            "Partial update is not supported. Use PUT for full update."
        )

    def destroy(self, request, *args, **kwargs):
        config = self.get_object()
        if config.name.startswith(PRESET_PREFIX):
            raise PermissionDenied("System-managed configs cannot be deleted")

        self.service.delete(config.external_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
