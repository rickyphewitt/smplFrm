from django.views.generic import TemplateView
from smplfrm.plugins.weather.weather import WeatherPlugin
from smplfrm.services.config_service import ConfigService

from smplfrm.settings import (
    SMPL_FRM_EXTERNAL_PORT,
    SMPL_FRM_HOST,
    SMPL_FRM_PROTOCOL,
)


class IndexView(TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        config = ConfigService().load_config()

        weather_enabled = "weather" in config.plugins
        weather_data = {
            "current_temp": "",
            "current_low_temp": "",
            "current_high_temp": "",
        }
        if weather_enabled:
            weather_data = WeatherPlugin().get_for_display()

        context = {
            "host": f"{SMPL_FRM_PROTOCOL}{SMPL_FRM_HOST}",
            "port": SMPL_FRM_EXTERNAL_PORT,
            "config_id": config.external_id,
            "config_name": config.name,
            "refresh_interval": config.image_refresh_interval,
            "transition_interval": config.image_transition_interval,
            "display_date": str(config.display_date).lower(),
            "display_clock": str(config.display_clock).lower(),
            "display_weather": str(weather_enabled).lower(),
            "weather_current_temp": weather_data["current_temp"],
            "current_low_temp": weather_data["current_low_temp"],
            "current_high_temp": weather_data["current_high_temp"],
            "plugin_spotify_enabled": str("spotify" in config.plugins).lower(),
            "image_zoom_effect": str(config.image_zoom_effect).lower(),
            "image_transition_type": config.image_transition_type,
        }

        return context
