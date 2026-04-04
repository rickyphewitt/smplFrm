from django.test import TestCase
from unittest.mock import patch, MagicMock

from smplfrm.models import Plugin
from smplfrm.services.plugin_service import PluginService


class TestPluginOnSettingsChanged(TestCase):

    def setUp(self):
        self.service = PluginService()
        self.plugin = Plugin.objects.get(name="weather")
        self.plugin.settings = {"coords": "63.17,-147.46", "temp_unit": "F"}
        self.plugin.save()

    @patch("smplfrm.plugins.weather.weather.WeatherPlugin.on_settings_changed")
    def test_update_calls_on_settings_changed(self, mock_hook):
        """Updating plugin settings via service should call on_settings_changed."""
        new_settings = {"coords": "40.71,-74.00", "temp_unit": "C"}
        self.plugin.settings = new_settings
        self.service.update(self.plugin)
        mock_hook.assert_called_once_with(new_settings)

    @patch("smplfrm.plugins.weather.weather.WeatherPlugin.on_settings_changed")
    def test_on_settings_changed_receives_new_settings(self, mock_hook):
        """on_settings_changed should receive the new settings dict."""
        new_settings = {"coords": "51.50,-0.12", "temp_unit": "C"}
        self.plugin.settings = new_settings
        self.service.update(self.plugin)
        args = mock_hook.call_args[0]
        self.assertEqual(args[0]["coords"], "51.50,-0.12")
        self.assertEqual(args[0]["temp_unit"], "C")
