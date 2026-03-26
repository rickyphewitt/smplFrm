import logging

from django.core.exceptions import PermissionDenied
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from smplfrm.models import Config
from smplfrm.services.config_service import ConfigService, PRESET_PREFIX
from smplfrm.views.serializers.v1.config_serializer import (
    ConfigSerializer,
)

logger = logging.getLogger(__name__)


class ConfigPagination(PageNumberPagination):
    page_size = 5


class ConfigViewSet(viewsets.ModelViewSet):

    queryset = Config.objects.all()
    serializer_class = ConfigSerializer
    lookup_field = "external_id"
    pagination_class = ConfigPagination

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ConfigService()

    def _get_config(self):
        return Config.objects.get(external_id=self.kwargs["external_id"], deleted=False)

    def create(self, request, *args, **kwargs):
        raise PermissionDenied()

    def update(self, request, *args, **kwargs):
        config = self._get_config()
        if config.name.startswith(PRESET_PREFIX):
            return Response(
                {"detail": "System-managed configs cannot be modified."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.service.list()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        raise PermissionDenied()

    def destroy(self, request, *args, **kwargs):
        config = self._get_config()
        if config.name.startswith(PRESET_PREFIX):
            return Response(
                {"detail": "System-managed configs cannot be deleted."},
                status=status.HTTP_403_FORBIDDEN,
            )
        config.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"])
    def apply(self, request):
        try:
            config = self.service.apply_preset()
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(config)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def activate(self, request, external_id=None):
        config = self.service.activate(external_id)
        serializer = self.get_serializer(config)
        return Response(serializer.data)
