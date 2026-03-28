from django.core.exceptions import PermissionDenied
from rest_framework import viewsets
from rest_framework.response import Response

from smplfrm.models import Plugin
from smplfrm.services.plugin_service import PluginService
from smplfrm.views.serializers.v1.plugin_serializer import PluginSerializer


class PluginViewSet(viewsets.ModelViewSet):

    queryset = Plugin.objects.all()
    serializer_class = PluginSerializer
    lookup_field = "external_id"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PluginService()

    def create(self, request, *args, **kwargs):
        raise PermissionDenied()

    def list(self, request, *args, **kwargs):
        queryset = self.service.list()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        plugin = self.get_object()
        serializer = self.get_serializer(plugin, data=request.data)
        serializer.is_valid(raise_exception=True)
        plugin.settings = serializer.validated_data.get("settings", plugin.settings)
        self.service.update(plugin)
        return Response(self.get_serializer(plugin).data)

    def partial_update(self, request, *args, **kwargs):
        raise PermissionDenied()

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied()
