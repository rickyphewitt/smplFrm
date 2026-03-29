from django.test import TestCase
from unittest.mock import patch, Mock

from smplfrm.models import Config, Plugin
from smplfrm.plugins.spotify import SpotifyPlugin


class TestSpotifyService(TestCase):

    @patch("smplfrm.plugins.spotify.spotify.SpotifyOAuth")
    def setUp(self, mock_spotify_oauth):
        from smplfrm.services.config_service import ConfigService

        config = ConfigService().load_config()
        config.plugins = ["spotify"]
        config.save()

        plugin = Plugin.objects.get(name="spotify")
        plugin.settings = {"client_id": "foo", "client_secret": "bar"}
        plugin.save()

        mock_spotify_oauth.return_value = Mock()
        self.mock_oauth = mock_spotify_oauth
        self.service = SpotifyPlugin()
        self.spotify_now_playing = {
            "currently_playing_type": "track",
            "item": {
                "artists": [{"name": "artist1"}, {"name": "artist2"}],
                "name": "songName",
            },
        }

    def test_spotify_missing_config(self):
        Plugin.objects.filter(name="spotify").update(
            settings={"client_id": "", "client_secret": ""}
        )
        missing_conf_service = SpotifyPlugin()
        self.assertFalse(getattr(missing_conf_service, "enabled"))

    @patch("smplfrm.plugins.spotify.spotify.Spotify")
    def test_spotify_returns_success(self, mock_spotify):
        mock_spotify_instance = Mock()
        mock_spotify.return_value = mock_spotify_instance
        mock_spotify_instance.current_user_playing_track.return_value = (
            self.spotify_now_playing
        )

        ret_value = self.service.get_now_playing()
        self.assertTrue(ret_value["success"])
        self.assertEqual(ret_value.get("artist"), "artist1")
        self.assertEqual(ret_value.get("song"), "songName")

    @patch("smplfrm.plugins.spotify.spotify.Spotify")
    def test_spotify_returns_success_unsupported_type(self, mock_spotify):
        mock_spotify_instance = Mock()
        mock_spotify.return_value = mock_spotify_instance
        mock_spotify_instance.current_user_playing_track.return_value = {
            "currently_playing_type": "not_supported"
        }

        ret_value = self.service.get_now_playing()
        self.assertTrue(ret_value["success"])
        self.assertEqual(ret_value.get("artist"), "Unsupported Type")
        self.assertEqual(ret_value.get("song"), "not_supported")

    @patch("smplfrm.plugins.spotify.spotify.Spotify")
    def test_spotify_returns_success_unsupported_type_episode(self, mock_spotify):
        mock_spotify_instance = Mock()
        mock_spotify.return_value = mock_spotify_instance
        mock_spotify_instance.current_user_playing_track.return_value = {
            "currently_playing_type": "episode"
        }

        ret_value = self.service.get_now_playing()
        self.assertTrue(ret_value["success"])
        self.assertEqual(ret_value.get("artist"), "Awesome")
        self.assertEqual(ret_value.get("song"), "Podcast")

    @patch("smplfrm.plugins.spotify.spotify.Spotify")
    def test_spotify_returns_exception(self, mock_spotify):
        mock_spotify.side_effect = Exception
        ret_value = self.service.get_now_playing()
        self.assertFalse(ret_value["success"])

    def test_spotify_callback(self):
        ret_value = self.service.callback("foo")
        self.assertTrue(ret_value["success"])

    def test_spotify_disabled_when_not_in_plugins(self):
        from smplfrm.services.config_service import ConfigService

        config = ConfigService().load_config()
        config.plugins = []
        config.save()
        disabled_service = SpotifyPlugin()
        self.assertFalse(getattr(disabled_service, "enabled"))
