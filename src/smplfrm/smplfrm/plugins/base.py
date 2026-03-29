class BasePlugin:
    """Base class for all smplFrm plugins."""

    def __init__(self, name: str, description: str, settings: dict = None):
        self.name = name
        self.description = description
        self._default_settings = settings if settings is not None else {}

    @property
    def enabled(self) -> bool:
        """Check if this plugin is enabled in the active config."""
        from smplfrm.services.config_service import ConfigService

        return self.name in ConfigService().load_config().plugins

    @property
    def plugin_settings(self) -> dict:
        """Load this plugin's settings from the database."""
        from smplfrm.services.plugin_service import PluginService

        return PluginService().read_by_name(self.name).settings

    @plugin_settings.setter
    def plugin_settings(self, value: dict):
        """Update this plugin's settings in the database."""
        from smplfrm.services.plugin_service import PluginService

        service = PluginService()
        plugin = service.read_by_name(self.name)
        plugin.settings = value
        service.update(plugin)

    def get_tasks(self) -> dict:
        """Return {task_name: task_function} for this plugin."""
        return {}

    def get_beat_schedule(self) -> dict:
        """Return Celery beat schedule entries for this plugin."""
        return {}
