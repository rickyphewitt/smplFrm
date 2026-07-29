from unittest.mock import Mock, patch

from django.test import TestCase

SPOTIFY_URI = "/api/v1/plugins/spotify"
STATE_SESSION_KEY = "spotify_oauth_state"


class TestSpotifyOAuthView(TestCase):
    def store_state(self, value="stored-state"):
        session = self.client.session
        session[STATE_SESSION_KEY] = value
        session.save()

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_auth_stores_state_and_returns_only_authorize_url(self, plugin_class):
        plugin_class.return_value.auth.return_value = {
            "success": True,
            "state": "generated-state-with-at-least-32-characters",
            "auth_url": "https://accounts.spotify.com/authorize?state=generated",
        }

        response = self.client.get(f"{SPOTIFY_URI}/auth")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"auth_url": ("https://accounts.spotify.com/authorize?state=generated")},
        )
        self.assertEqual(
            self.client.session[STATE_SESSION_KEY],
            "generated-state-with-at-least-32-characters",
        )

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_callback_rejects_missing_request_state_without_exchange(
        self, plugin_class
    ):
        self.store_state()

        response = self.client.get(
            f"{SPOTIFY_URI}/callback", {"code": "authorization-code"}
        )

        self.assertEqual(response.status_code, 403)
        plugin_class.assert_not_called()

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_callback_rejects_missing_session_state_without_exchange(
        self, plugin_class
    ):
        response = self.client.get(
            f"{SPOTIFY_URI}/callback",
            {"code": "authorization-code", "state": "request-state"},
        )

        self.assertEqual(response.status_code, 403)
        plugin_class.assert_not_called()

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_invalid_callback_state_renders_recovery_page(self, plugin_class):
        response = self.client.get(
            f"{SPOTIFY_URI}/callback",
            {"code": "authorization-code", "state": "untrusted-state"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(response["Content-Type"].startswith("text/html"))
        self.assertContains(
            response,
            "Authorization failed. Please try connecting Spotify again.",
            status_code=403,
        )
        self.assertContains(response, 'href="/"', status_code=403)
        plugin_class.assert_not_called()

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_callback_rejects_mismatched_state_without_exchange(self, plugin_class):
        self.store_state("expected-state")

        response = self.client.get(
            f"{SPOTIFY_URI}/callback",
            {"code": "authorization-code", "state": "attacker-state"},
        )

        self.assertEqual(response.status_code, 403)
        plugin_class.assert_not_called()

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_callback_consumes_matching_state_and_redirects(self, plugin_class):
        self.store_state("matching-state")
        plugin_class.return_value.callback.return_value = {"success": True}

        response = self.client.get(
            f"{SPOTIFY_URI}/callback",
            {"code": "authorization-code", "state": "matching-state"},
        )

        self.assertEqual(response.status_code, 302)
        plugin_class.return_value.callback.assert_called_once_with("authorization-code")
        self.assertNotIn(STATE_SESSION_KEY, self.client.session)

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_callback_state_cannot_be_replayed(self, plugin_class):
        self.store_state("one-time-state")
        plugin_class.return_value.callback.return_value = {"success": True}
        query = {"code": "authorization-code", "state": "one-time-state"}

        first_response = self.client.get(f"{SPOTIFY_URI}/callback", query)
        second_response = self.client.get(f"{SPOTIFY_URI}/callback", query)

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 403)
        plugin_class.return_value.callback.assert_called_once_with("authorization-code")

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_matching_state_without_code_is_consumed_without_exchange(
        self, plugin_class
    ):
        self.store_state("matching-state")

        response = self.client.get(
            f"{SPOTIFY_URI}/callback", {"state": "matching-state"}
        )

        self.assertEqual(response.status_code, 400)
        plugin_class.assert_not_called()
        self.assertNotIn(STATE_SESSION_KEY, self.client.session)


class TestSpotifyAuthorizationResponses(TestCase):
    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_expired_token_returns_typed_unauthorized_response(self, plugin_class):
        plugin_class.return_value.get_now_playing.return_value = {
            "success": False,
            "error": "reauth_required",
        }

        response = self.client.get(f"{SPOTIFY_URI}/now_playing")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {
                "error": "spotify_authorization_required",
                "reason": "expired",
            },
        )

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_missing_token_returns_typed_unauthorized_response(self, plugin_class):
        plugin_class.return_value.get_now_playing.return_value = {
            "success": False,
            "error": "authorization_required",
        }

        response = self.client.get(f"{SPOTIFY_URI}/now_playing")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {
                "error": "spotify_authorization_required",
                "reason": "missing",
            },
        )

    @patch("smplfrm.views.api.plugins.v1.spotify.spotify_view.SpotifyPlugin")
    def test_generic_failure_remains_precondition_failed(self, plugin_class):
        plugin_class.return_value.get_now_playing.return_value = {"success": False}

        response = self.client.get(f"{SPOTIFY_URI}/now_playing")

        self.assertEqual(response.status_code, 412)
