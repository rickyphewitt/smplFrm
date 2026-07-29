from django.test import TestCase
from unittest.mock import Mock, patch


class TestSpotifyView(TestCase):
    def setUp(self):
        self.uri = "/api/v1/plugins/spotify"
        self.now_playing_success = {
            "success": True,
            "artist": "artist1",
            "song": "song",
        }
        self.success_false = {"success": False}

    def store_oauth_state(self, state):
        session = self.client.session
        session["spotify_oauth_state"] = state
        session.save()

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_now_playing_success(self, mock_spotify_service):
        mock_spotify_instance = Mock()
        mock_spotify_service.return_value = mock_spotify_instance
        mock_spotify_instance.get_now_playing.return_value = self.now_playing_success

        response = self.client.get(f"{self.uri}/now_playing")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["artist"], "artist1")
        self.assertEqual(response.json()["song"], "song")

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_now_playing_failure(self, mock_spotify_service):
        mock_spotify_instance = Mock()
        mock_spotify_service.return_value = mock_spotify_instance
        mock_spotify_instance.get_now_playing.return_value = self.success_false

        response = self.client.get(f"{self.uri}/now_playing")

        self.assertEqual(response.status_code, 412)

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_callback_success(self, mock_spotify_service):
        state = "matching-state"
        self.store_oauth_state(state)
        mock_spotify_instance = Mock()
        mock_spotify_service.return_value = mock_spotify_instance
        mock_spotify_instance.callback.return_value = {"success": True}

        response = self.client.get(
            f"{self.uri}/callback",
            {"code": "authorization-code", "state": state},
        )

        self.assertEqual(response.status_code, 302)

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_callback_failure(self, mock_spotify_service):
        state = "matching-state"
        self.store_oauth_state(state)
        mock_spotify_instance = Mock()
        mock_spotify_service.return_value = mock_spotify_instance
        mock_spotify_instance.callback.return_value = self.success_false

        response = self.client.get(
            f"{self.uri}/callback",
            {"code": "authorization-code", "state": state},
        )

        self.assertEqual(response.status_code, 412)
