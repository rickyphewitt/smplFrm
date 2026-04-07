from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

from smplfrm.plugins.weather.weather import WeatherPlugin


class TestWeatherEmptyCoords(TestCase):
    """Regression tests for empty/invalid coordinates (#163)."""

    @patch("smplfrm.plugins.weather.weather.BasePlugin.get_plugin_settings")
    def test_configure_with_empty_coords_raises(self, mock_settings):
        mock_settings.return_value = {"coords": ""}
        plugin = WeatherPlugin()
        with self.assertRaises(ValueError):
            plugin.configure()

    @patch("smplfrm.plugins.weather.weather.BasePlugin.get_plugin_settings")
    def test_configure_with_single_value_raises(self, mock_settings):
        mock_settings.return_value = {"coords": "63.1786"}
        plugin = WeatherPlugin()
        with self.assertRaises(ValueError):
            plugin.configure()

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_view_returns_400_when_coords_invalid(self, mock_plugin_cls):
        mock_plugin_cls.return_value.get_for_display.side_effect = ValueError(
            "Invalid coordinates"
        )
        client = APIClient()
        response = client.get("/api/v1/plugins/weather")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
