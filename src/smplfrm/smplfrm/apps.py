from django.apps import AppConfig


class SmplFrmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "smplfrm"

    def ready(self):
        from django.db.models.signals import post_migrate

        post_migrate.connect(self._sync_on_startup, sender=self)

    @staticmethod
    def _sync_on_startup(sender, **kwargs):
        from smplfrm.services.config_service import ConfigService
        from smplfrm.services.plugin_service import PluginService

        ConfigService().sync_presets()
        PluginService().sync_plugins()
