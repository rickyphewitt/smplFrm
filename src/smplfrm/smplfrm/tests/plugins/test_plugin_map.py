from django.test import TestCase

from smplfrm.plugins import get_plugin_map
from smplfrm.plugins.spotify.spotify import SpotifyPlugin
from smplfrm.plugins.weather.weather import WeatherPlugin


class TestGetPluginMap(TestCase):

    def test_returns_dict_keyed_by_name(self):
        plugin_map = get_plugin_map()
        self.assertIn("spotify", plugin_map)
        self.assertIn("weather", plugin_map)

    def test_values_are_plugin_instances(self):
        plugin_map = get_plugin_map()
        self.assertIsInstance(plugin_map["spotify"], SpotifyPlugin)
        self.assertIsInstance(plugin_map["weather"], WeatherPlugin)
