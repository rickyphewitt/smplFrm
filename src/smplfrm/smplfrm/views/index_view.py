from django.views.generic import TemplateView
from smplfrm.services.config_service import ConfigService
from smplfrm.services.version_service import VersionService

from smplfrm.settings import (
    SMPL_FRM_EXTERNAL_PORT,
    SMPL_FRM_HOST,
    SMPL_FRM_PROTOCOL,
)


class IndexView(TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        from zoneinfo import available_timezones

        config = ConfigService().load_config()

        context = {
            "host": f"{SMPL_FRM_PROTOCOL}{SMPL_FRM_HOST}",
            "port": SMPL_FRM_EXTERNAL_PORT,
            "config_id": config.external_id,
            "config_name": config.name,
            "refresh_interval": config.image_refresh_interval,
            "transition_interval": config.image_transition_interval,
            "display_date": str(config.display_date).lower(),
            "display_clock": str(config.display_clock).lower(),
            "image_zoom_effect": str(config.image_zoom_effect).lower(),
            "image_transition_type": config.image_transition_type,
            "plugins": config.plugins,
            "timezones": sorted(available_timezones()),
            "version": VersionService().get_version(),
        }

        return context
