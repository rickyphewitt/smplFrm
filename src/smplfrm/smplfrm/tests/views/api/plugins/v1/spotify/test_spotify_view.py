from unittest.mock import Mock, patch

from django.test import TestCase


class TestSpotifyView(TestCase):

    @patch("smplfrm.plugins.spotify.spotify.SpotifyPlugin")
    def setUp(self, mock_spotify_service):
        self.uri = "/api/v1/plugins/spotify"
        mock_spotify_service = Mock()
        self.service = mock_spotify_service
        self.now_playing_success = {
            "success": "true",
            "artist": "artist1",
            "song": "song",
        }
        self.success_false = {"success": False}

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_now_playing_success(self, mock_spotify_service):
        mock_spotify_instance = Mock()
        mock_spotify_service.return_value = mock_spotify_instance
        mock_spotify_instance.get_now_playing.return_value = self.now_playing_success

        response = self.client.get(f"{self.uri}/now_playing")
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 200)
        returned_json = response.json()
        self.assertEqual(
            returned_json.get("artist"), self.now_playing_success.get("artist")
        )
        self.assertEqual(
            returned_json.get("song"), self.now_playing_success.get("song")
        )

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_now_playing_exception(self, mock_spotify_service):
        mock_spotify_instance = Mock()
        mock_spotify_service.return_value = mock_spotify_instance
        mock_spotify_instance.get_now_playing.return_value = self.success_false

        response = self.client.get(f"{self.uri}/now_playing")
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 412)

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_callback_exception(self, mock_spotify_service):
        mock_spotify_instance = Mock()
        mock_spotify_service.return_value = mock_spotify_instance
        mock_spotify_instance.callback.return_value = {"success": True}

        response = self.client.get(f"{self.uri}/callback")
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 200)

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_callback_exception(self, mock_spotify_service):
        mock_spotify_instance = Mock()
        mock_spotify_service.return_value = mock_spotify_instance
        mock_spotify_instance.callback.return_value = self.success_false

        response = self.client.get(f"{self.uri}/callback")
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 412)
