"""Plugin configuration API views.

Provides JSON:API endpoints for plugin list, detail, and update.
Create, partial update, and delete are forbidden.
"""

import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import viewsets
from rest_framework.response import Response

from smplfrm.jsonapi import (
    jsonapi_exception_handler,
    SECRET_MASK,
)
from smplfrm.views.serializers.v1.plugin_serializer import PluginSerializer
from smplfrm.models import Plugin
from smplfrm.plugins import PLUGIN_REGISTRY
from smplfrm.services.plugin_service import PluginService

logger = logging.getLogger(__name__)


class PluginViewSet(viewsets.ModelViewSet):
    """JSON:API Plugin configuration endpoint.

    Supports:
    - GET /plugins - list all plugins (paginated)
    - GET /plugins/{id} - plugin detail
    - PUT /plugins/{id} - full update of plugin settings

    Forbidden:
    - POST (create)
    - PATCH (partial update)
    - DELETE

    Security:
    - Returns 403 for non-existent resources to prevent enumeration attacks
    """

    queryset = Plugin.objects.filter(deleted=False).order_by("name")
    serializer_class = PluginSerializer
    lookup_field = "external_id"
    resource_name = "plugins"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = PluginService()

    def get_exception_handler(self):
        return jsonapi_exception_handler

    def get_object(self):
        """Return 403 instead of 404 to prevent resource enumeration."""
        try:
            return super().get_object()
        except Http404:
            raise PermissionDenied("Access denied")

    def create(self, request, *args, **kwargs):
        raise PermissionDenied("Plugin creation is not supported")

    def partial_update(self, request, *args, **kwargs):
        raise PermissionDenied(
            "Partial update is not supported. Use PUT for full update."
        )

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied("Plugin deletion is not supported")

    def _get_secret_keys(self, plugin_name):
        """Return set of setting keys marked as type 'password' for a plugin."""
        for cls in PLUGIN_REGISTRY:
            plugin = cls()
            if plugin.name == plugin_name:
                return {
                    field["key"]
                    for field in plugin.get_settings_schema()
                    if field.get("type") == "password"
                }
        return set()

    def update(self, request, *args, **kwargs):
        """Full update of plugin settings.

        Retains original secret values when the masked placeholder is submitted.
        """
        plugin = self.get_object()
        serializer = self.get_serializer(plugin, data=request.data)
        serializer.is_valid(raise_exception=True)

        new_settings = serializer.validated_data.get("settings", plugin.settings)

        # Retain original secret values when the masked placeholder is submitted
        secret_keys = self._get_secret_keys(plugin.name)
        if secret_keys and new_settings:
            for key in secret_keys:
                if new_settings.get(key) == SECRET_MASK:
                    new_settings[key] = plugin.settings.get(key, "")

        plugin.settings = new_settings
        self.service.update(plugin)
        return Response(self.get_serializer(plugin).data)
