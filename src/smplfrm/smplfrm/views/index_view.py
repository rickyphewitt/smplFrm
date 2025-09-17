from django.views.generic import TemplateView
from smplfrm.services.weather_service import WeatherService

from smplfrm.settings import (
    SMPL_FRM_EXTERNAL_PORT,
    SMPL_FRM_HOST,
    SMPL_FRM_IMAGE_REFRESH_INTERVAL,
    SMPL_FRM_PROTOCOL,
    SMPL_FRM_DISPLAY_DATE,
    SMPL_FRM_DISPLAY_CLOCK,
    SMPL_FRM_IMAGE_TRANSITION_INTERVAL,
    SMPL_FRM_PLUGINS_SPOTIFY_ENABLED,
)


class IndexView(TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        """
        Sets the variables in the template
        :param kwargs:
        :return:
        """

        weather_data = WeatherService().get_for_display()

        context = {
            "host": f"{SMPL_FRM_PROTOCOL}{SMPL_FRM_HOST}",
            "port": SMPL_FRM_EXTERNAL_PORT,
            "refresh_interval": SMPL_FRM_IMAGE_REFRESH_INTERVAL,
            "transition_interval": SMPL_FRM_IMAGE_TRANSITION_INTERVAL,
            "display_date": str(SMPL_FRM_DISPLAY_DATE).lower(),
            "display_clock": str(SMPL_FRM_DISPLAY_CLOCK).lower(),
            "weather_current_temp": weather_data["current_temp"],
            "current_low_temp": weather_data["current_low_temp"],
            "current_high_temp": weather_data["current_high_temp"],
            "plugin_spotify_enabled": str(SMPL_FRM_PLUGINS_SPOTIFY_ENABLED).lower(),
        }

        return context
