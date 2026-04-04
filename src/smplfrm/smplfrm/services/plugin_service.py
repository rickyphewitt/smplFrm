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

        from smplfrm.plugins import get_all_plugins

        for p in get_all_plugins():
            if p.name == plugin.name:
                p.on_settings_changed(plugin.settings)
                break

        return plugin

    def delete(self, ext_id: str) -> None:
        raise NotImplementedError("Plugin deletion not supported")

    def destroy(self, ext_id: str) -> None:
        raise NotImplementedError("Plugin destruction not supported")

    def sync_plugins(self) -> None:
        """Sync plugin rows from PLUGIN_REGISTRY to the database.

        Environment variables take priority over DB values when explicitly set.
        Uses plugin.get_env_overrides() which scans for SMPL_FRM_PLUGINS_{NAME}_ prefix.
        Existing DB settings for keys without an env var are preserved.
        """
        from smplfrm.plugins import get_all_plugins

        for plugin in get_all_plugins():
            obj, created = Plugin.objects.get_or_create(
                name=plugin.name,
                defaults={"description": plugin.description, "settings": {}},
            )

            env_overrides = plugin.get_env_overrides()
            if env_overrides:
                obj.settings = {**obj.settings, **env_overrides}
                obj.save()
                logger.info(
                    f"Updated plugin {plugin.name} with env overrides: {list(env_overrides.keys())}"
                )

            logger.info(f"Synced plugin: {plugin.name}")
