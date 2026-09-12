import hashlib

from django.test import TestCase
from unittest.mock import Mock, patch


class TestSpotifyView(TestCase):
    def setUp(self):
        self.uri = "/api/v1/plugins/spotify"
        self.status_success = {
            "success": True,
            "is_playing": True,
            "track": {
                "uri": "spotify:track:abc123",
                "artist": "artist1",
                "song": "song",
            },
        }
        self.status_not_playing = {
            "success": True,
            "is_playing": False,
            "track": None,
        }
        self.success_false = {"success": False}

    def store_oauth_state(self, state):
        session = self.client.session
        session["spotify_oauth_state"] = state
        session.save()

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_status_success_with_track(self, mock_spotify_service):
        """Test status endpoint returns JSON:API format with track."""
        mock_spotify_instance = Mock()
        mock_spotify_service.return_value = mock_spotify_instance
        mock_spotify_instance.get_now_playing.return_value = self.status_success

        response = self.client.get(f"{self.uri}/status")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify JSON:API structure
        self.assertIn("data", data)
        self.assertEqual(data["data"]["type"], "spotify_status")
        self.assertEqual(data["data"]["id"], "current")
        self.assertTrue(data["data"]["attributes"]["is_playing"])

        # Verify relationship
        self.assertIn("relationships", data["data"])
        self.assertIn("track", data["data"]["relationships"])
        track_rel = data["data"]["relationships"]["track"]["data"]
        self.assertEqual(track_rel["type"], "spotify_tracks")

        # Verify track ID is opaque hash
        expected_id = hashlib.sha256(b"spotify:track:abc123").hexdigest()[:16]
        self.assertEqual(track_rel["id"], expected_id)

        # Verify included track
        self.assertIn("included", data)
        self.assertEqual(len(data["included"]), 1)
        track = data["included"][0]
        self.assertEqual(track["type"], "spotify_tracks")
        self.assertEqual(track["attributes"]["artist"], "artist1")
        self.assertEqual(track["attributes"]["song"], "song")

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_status_not_playing(self, mock_spotify_service):
        """Test status endpoint when nothing is playing."""
        mock_spotify_instance = Mock()
        mock_spotify_service.return_value = mock_spotify_instance
        mock_spotify_instance.get_now_playing.return_value = self.status_not_playing

        response = self.client.get(f"{self.uri}/status")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertFalse(data["data"]["attributes"]["is_playing"])
        self.assertIsNone(data["data"]["relationships"]["track"]["data"])
        self.assertNotIn("included", data)

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_status_failure(self, mock_spotify_service):
        """Test status endpoint returns JSON:API error on failure."""
        mock_spotify_instance = Mock()
        mock_spotify_service.return_value = mock_spotify_instance
        mock_spotify_instance.get_now_playing.return_value = self.success_false

        response = self.client.get(f"{self.uri}/status")

        self.assertEqual(response.status_code, 412)
        data = response.json()
        self.assertIn("errors", data)
        self.assertEqual(data["errors"][0]["code"], "spotify_unavailable")

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_status_authorization_required(self, mock_spotify_service):
        """Test status endpoint returns 401 when authorization required."""
        mock_spotify_instance = Mock()
        mock_spotify_service.return_value = mock_spotify_instance
        mock_spotify_instance.get_now_playing.return_value = {
            "success": False,
            "error": "authorization_required",
        }

        response = self.client.get(f"{self.uri}/status")

        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn("errors", data)
        self.assertEqual(data["errors"][0]["code"], "spotify_authorization_required")
        self.assertIn("missing", data["errors"][0]["detail"])

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_status_reauth_required(self, mock_spotify_service):
        """Test status endpoint returns 401 when reauth required."""
        mock_spotify_instance = Mock()
        mock_spotify_service.return_value = mock_spotify_instance
        mock_spotify_instance.get_now_playing.return_value = {
            "success": False,
            "error": "reauth_required",
        }

        response = self.client.get(f"{self.uri}/status")

        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn("expired", data["errors"][0]["detail"])

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
