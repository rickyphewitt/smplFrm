from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

from smplfrm.models import Plugin


class TestWeatherView(TestCase):

    def setUp(self):
        self.client = APIClient()

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_weather_endpoint_returns_display_data(self, mock_plugin_cls):
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "current_temp": "72 °F",
            "current_low_temp": "55°F",
            "current_high_temp": "80°F",
        }

        response = self.client.get("/api/v1/plugins/weather")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["current_temp"], "72 °F")
        self.assertEqual(data["current_low_temp"], "55°F")
        self.assertEqual(data["current_high_temp"], "80°F")
