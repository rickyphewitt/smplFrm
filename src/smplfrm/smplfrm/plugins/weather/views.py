import json

from django.http import HttpResponse
from rest_framework import viewsets

from smplfrm.plugins.weather.weather import WeatherPlugin


class WeatherView(viewsets.ViewSet):

    def list(self, *args, **kwargs):
        plugin = WeatherPlugin()
        try:
            data = plugin.get_for_display()
        except ValueError as e:
            return HttpResponse(
                json.dumps({"error": str(e)}),
                content_type="application/json",
                status=400,
            )
        return HttpResponse(
            json.dumps(data),
            content_type="application/json",
        )
