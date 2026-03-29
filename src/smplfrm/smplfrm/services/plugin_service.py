import logging
from typing import Any, Dict

from django.db.models import QuerySet

from smplfrm.models import Plugin
from .base_service import BaseService

logger = logging.getLogger(__name__)


class PluginService(BaseService):
    """Service for managing Plugin configurations."""

    def create(self, data: Dict[str, Any]) -> Plugin:
        """Not supported for Plugin."""
        raise NotImplementedError("Plugin creation not supported")

    def read(self, ext_id: str, deleted: bool = False) -> Plugin:
        return Plugin.objects.get(external_id=ext_id, deleted=deleted)

    def read_by_name(self, name: str) -> Plugin:
        return Plugin.objects.get(name=name, deleted=False)

    def list(self, **kwargs) -> QuerySet:
        return Plugin.objects.filter(deleted=False).order_by("name")

    def update(self, plugin: Plugin) -> Plugin:
        logger.info(f"Updating plugin {plugin.name}")
        plugin.save()
        return plugin

    def delete(self, ext_id: str) -> None:
        raise NotImplementedError("Plugin deletion not supported")

    def destroy(self, ext_id: str) -> None:
        raise NotImplementedError("Plugin destruction not supported")

    def sync_plugins(self) -> None:
        """Sync plugin rows from PLUGIN_REGISTRY to the database.

        Environment variables always take priority over DB values for
        plugin settings. On every startup, settings are overwritten
        with env var values.
        """
        from smplfrm.plugins import get_all_plugins
        from smplfrm.settings import (
            SMPL_FRM_WEATHER_COORDS,
            SMPL_FRM_WEATHER_TEMP_UNIT,
            SMPL_FRM_WEATHER_PRECIP_UNIT,
            SMPL_FRM_WEATHER_WINDSPEED_UNIT,
            SMPL_FRM_PLUGINS_SPOTIFY_CLIENT_ID,
            SMPL_FRM_PLUGINS_SPOTIFY_CLIENT_SECRET,
        )

        env_settings = {
            "weather": {
                "coords": SMPL_FRM_WEATHER_COORDS,
                "temp_unit": SMPL_FRM_WEATHER_TEMP_UNIT,
                "precip_unit": SMPL_FRM_WEATHER_PRECIP_UNIT,
                "windspeed_unit": SMPL_FRM_WEATHER_WINDSPEED_UNIT,
            },
            "spotify": {
                "client_id": SMPL_FRM_PLUGINS_SPOTIFY_CLIENT_ID,
                "client_secret": SMPL_FRM_PLUGINS_SPOTIFY_CLIENT_SECRET,
            },
        }

        for plugin in get_all_plugins():
            settings_from_env = env_settings.get(plugin.name, {})
            obj, created = Plugin.objects.get_or_create(
                name=plugin.name,
                defaults={
                    "description": plugin.description,
                    "settings": settings_from_env,
                },
            )
            if not created:
                obj.settings = settings_from_env
                obj.save()
            logger.info(f"Synced plugin: {plugin.name}")
            if created:
                logger.info(f"Created plugin: {plugin.name} (seeded from env vars)")
            else:
                logger.info(f"Synced plugin: {plugin.name}")
