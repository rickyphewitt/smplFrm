import logging
import os

logger = logging.getLogger(__name__)


class BasePlugin:
    """Base class for all smplFrm plugins."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self._configured = False

    def configure(self):
        """Load settings from DB. Called lazily on first use."""
        if self._configured:
            return
        self._configured = True

    def _ensure_configured(self):
        """Ensure configure() has been called."""
        if not self._configured:
            self.configure()

    def get_env_overrides(self):
        """Return dict of environment variables that override plugin settings.

        Scans os.environ for keys matching SMPL_FRM_PLUGINS_{NAME}_ prefix.
        Empty values are skipped with a warning.
        Subclasses can override this for custom env var mapping.
        """
        plugin_env_prefix = f"SMPL_FRM_PLUGINS_{self.name.upper()}_"
        overrides = {}
        for key, value in os.environ.items():
            if key.startswith(plugin_env_prefix):
                clean_key = key[len(plugin_env_prefix) :].lower()
                if value:
                    overrides[clean_key] = value
                else:
                    logger.warning(f"Env var {key} is set but empty, skipping")
        return overrides

    def is_enabled(self) -> bool:
        """Check if this plugin is enabled in the active config."""
        from smplfrm.services.config_service import ConfigService

        return self.name in ConfigService().load_config().plugins

    def get_plugin_settings(self) -> dict:
        """Load this plugin's settings from the database."""
        from smplfrm.services.plugin_service import PluginService

        return PluginService().read_by_name(self.name).settings

    def update_plugin_settings(self, value: dict):
        """Update this plugin's settings in the database."""
        from smplfrm.services.plugin_service import PluginService

        service = PluginService()
        plugin = service.read_by_name(self.name)
        plugin.settings = value
        service.update(plugin)

    def get_tasks(self) -> dict:
        """Return {task_name: task_function} for this plugin."""
        return {}

    def get_startup_tasks(self) -> dict:
        """Return {task_name: task_function} to run on worker startup."""
        return {}

    def get_beat_schedule(self) -> dict:
        """Return Celery beat schedule entries for this plugin."""
        return {}

    def get_settings_schema(self) -> list:
        """Return list of field definitions for the plugin settings form.

        Each field is a dict with:
            key: settings dict key
            label: display label
            type: text, password, select, toggle
            options: list of values (for select type)
            action: optional JS action handler name (e.g. geolocation)
        """
        return []
