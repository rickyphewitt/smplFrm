"""Weather plugin JSON:API view.

Provides the /api/v1/plugins/weather/current endpoint returning a JSON:API
singleton resource with type "weather" and id "current".
"""

import logging

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from smplfrm.jsonapi import (
    JsonApiRenderer,
    JsonApiParser,
    StrictQueryMixin,
    WeatherUnavailableError,
    jsonapi_exception_handler,
)
from smplfrm.plugins.weather.serializers import WeatherSerializer
from smplfrm.plugins.weather.weather import WeatherPlugin

logger = logging.getLogger(__name__)


class WeatherView(StrictQueryMixin, viewsets.ViewSet):
    """JSON:API Weather endpoint.

    Returns a singleton resource at /weather/current with current weather data.
    No query parameters are accepted.
    """

    renderer_classes = [JsonApiRenderer]
    parser_classes = [JsonApiParser]
    serializer_class = WeatherSerializer
    resource_name = "weather"

    def get_exception_handler(self):
        return jsonapi_exception_handler

    allowed_query_params: set[str] = set()

    @action(detail=False, methods=["get"], url_path="current", url_name="current")
    def current(self, request, *args, **kwargs):
        """Return current weather as a JSON:API singleton resource."""
        plugin = WeatherPlugin()
        try:
            weather_data = plugin.get_for_display()
        except ValueError as e:
            logger.error("Weather plugin error: %s", e, exc_info=True)
            raise WeatherUnavailableError()
        except Exception as e:
            logger.error("Unexpected weather error: %s", e, exc_info=True)
            raise

        weather_data["id"] = "current"
        serializer = self.serializer_class(weather_data)
        return Response(serializer.data)
