from django.test import TestCase
from unittest.mock import patch

from smplfrm.plugins.weather.weather import WeatherPlugin


class TestWeatherOnSettingsChanged(TestCase):

    @patch("smplfrm.plugins.base.BasePlugin.dispatch_task")
    def test_on_settings_changed_dispatches_refresh(self, mock_dispatch):
        """WeatherPlugin.on_settings_changed should trigger a weather refresh."""
        plugin = WeatherPlugin()
        plugin.on_settings_changed({"coords": "40.71,-74.00", "temp_unit": "C"})
        mock_dispatch.assert_called_once_with("refresh_weather")

    @patch("smplfrm.plugins.base.BasePlugin.dispatch_task")
    def test_on_settings_changed_with_empty_settings(self, mock_dispatch):
        """on_settings_changed should still dispatch refresh even with empty settings."""
        plugin = WeatherPlugin()
        plugin.on_settings_changed({})
        mock_dispatch.assert_called_once_with("refresh_weather")
