from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from smplfrm.models import Plugin


class TestWeatherOnSettingsChanged(TestCase):
    """WeatherPlugin.on_settings_changed() should trigger refresh_weather task."""

    @patch("smplfrm.plugins.base.BasePlugin.dispatch_task")
    def test_on_settings_changed_triggers_task(self, mock_dispatch):
        from smplfrm.plugins.weather.weather import WeatherPlugin

        plugin = WeatherPlugin()
        plugin.on_settings_changed({"coords": "40.71,-74.00"})
        mock_dispatch.assert_called_once_with("refresh_weather")


class TestWeatherSettingsRefreshAPI(TestCase):
    """Regression: weather data must refresh after saving plugin settings (issue #153)."""

    def setUp(self):
        self.client = APIClient()
        Plugin.objects.all().delete()
        self.plugin = Plugin.objects.create(
            name="weather",
            description="Weather data",
            settings={"coords": "63.17,-147.46"},
        )
        self.url = f"/api/v1/plugins/{self.plugin.external_id}"

    @patch("smplfrm.plugins.base.BasePlugin.dispatch_task")
    def test_update_weather_plugin_triggers_refresh(self, mock_dispatch):
        """Saving weather settings should trigger a refresh_weather task."""
        self.client.put(
            self.url,
            {
                "name": "weather",
                "description": "Weather data",
                "settings": {"coords": "40.71,-74.00"},
            },
            content_type="application/json",
        )
        mock_dispatch.assert_called_once_with("refresh_weather")

    @patch("smplfrm.plugins.base.BasePlugin.dispatch_task")
    def test_update_non_weather_plugin_no_refresh(self, mock_dispatch):
        """Saving a non-weather plugin should not trigger weather refresh."""
        other = Plugin.objects.create(
            name="spotify",
            description="Spotify",
            settings={},
        )
        self.client.put(
            f"/api/v1/plugins/{other.external_id}",
            {
                "name": "spotify",
                "description": "Spotify",
                "settings": {"token": "abc"},
            },
            content_type="application/json",
        )
        mock_dispatch.assert_not_called()
