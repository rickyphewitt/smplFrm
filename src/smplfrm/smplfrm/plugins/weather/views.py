import json

from django.http import HttpResponse
from rest_framework import viewsets

from smplfrm.plugins.weather.weather import WeatherPlugin


class WeatherView(viewsets.ViewSet):

    def list(self, *args, **kwargs):
        plugin = WeatherPlugin()
        return HttpResponse(
            json.dumps(plugin.get_for_display()),
            content_type="application/json",
        )
