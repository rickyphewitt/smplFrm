import logging

from django.core.exceptions import PermissionDenied
from rest_framework import viewsets
from smplfrm.models import Config
from smplfrm.services.config_service import ConfigService
from smplfrm.views.serializers.v1.config_serializer import (
    ConfigSerializer,
)

logger = logging.getLogger(__name__)


class ConfigViewSet(viewsets.ModelViewSet):

    queryset = Config.objects.all()
    serializer_class = ConfigSerializer
    lookup_field = "external_id"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ConfigService()

    # Only allow retrieve and update (PUT)
    def create(self, request, *args, **kwargs):
        raise PermissionDenied()

    def list(self, request, *args, **kwargs):
        raise PermissionDenied()

    def partial_update(self, request, *args, **kwargs):
        raise PermissionDenied()

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied()
