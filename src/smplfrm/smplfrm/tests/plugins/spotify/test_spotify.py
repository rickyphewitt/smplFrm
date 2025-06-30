
from django.test import TestCase
from unittest.mock import patch, Mock

from smplfrm.plugins.spotify import SpotifyPlugin


class TestSpotifyService(TestCase):

    @patch("smplfrm.plugins.spotify.spotify.SpotifyOAuth")
    def setUp(self, mock_spotify_oauth):
        mock_spotify_oauth.return_value = Mock()
        self.mock_oauth = mock_spotify_oauth
        self.service = SpotifyPlugin()
        self.spotify_now_playing = {
            "item": {
                "artists": [
                    {"name": "artist1"},
                    {"name": "artist2"}
                ],
                "name": "songName"
            }
        }

    @patch("smplfrm.plugins.spotify.spotify.Spotify")
    def test_spotify_returns_success(self, mock_spotify):
        mock_spotify_instance = Mock()
        mock_spotify.return_value = mock_spotify_instance

        mock_spotify_instance.current_user_playing_track.return_value = self.spotify_now_playing

        ret_value = self.service.get_now_playing()
        self.assertIsNotNone(ret_value, "spotify should have returned data")
        self.assertTrue(ret_value["success"])
        self.assertEqual(ret_value.get("artist"), "artist1", "Artist Should be set")
        self.assertEqual(ret_value.get("song"), "songName", "Song should be set")

    @patch("smplfrm.plugins.spotify.spotify.Spotify")
    def test_spotify_returns_exception(self, mock_spotify):
        mock_spotify_instance = Mock(side_effect=Exception)
        mock_spotify.side_effect = mock_spotify_instance

        ret_value = self.service.get_now_playing()
        self.assertIsNotNone(ret_value, "spotify should have returned data")
        self.assertFalse(ret_value["success"])

    def test_spotify_callback(self):

        ret_value = self.service.callback("foo")
        self.assertIsNotNone(ret_value, "spotify should have returned data")
        self.assertTrue(ret_value["success"])