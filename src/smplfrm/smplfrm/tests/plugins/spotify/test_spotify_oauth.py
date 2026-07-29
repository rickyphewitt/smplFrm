from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from spotipy.exceptions import SpotifyOauthError

from smplfrm.models import Plugin
from smplfrm.plugins.spotify import SpotifyPlugin
from smplfrm.plugins.spotify.spotify import SpotifyCacheHandler


class SpotifyPluginTestCase(TestCase):
    def setUp(self):
        from smplfrm.services.config_service import ConfigService

        config = ConfigService().load_config()
        config.plugins = ["spotify"]
        config.save()

        plugin = Plugin.objects.get(name="spotify")
        plugin.settings = {"client_id": "client-id", "client_secret": "secret"}
        plugin.save()

    def build_plugin(self):
        with patch("smplfrm.plugins.spotify.spotify.SpotifyOAuth") as oauth_class:
            auth_manager = Mock()
            oauth_class.return_value = auth_manager
            plugin = SpotifyPlugin()
            plugin.configure()
        plugin.cache_manager = Mock()
        return plugin, auth_manager


class TestSpotifyOAuthState(SpotifyPluginTestCase):
    def test_auth_generates_unique_state_and_adds_it_to_authorize_url(self):
        plugin, auth_manager = self.build_plugin()
        auth_manager.get_authorize_url.side_effect = ["first-url", "second-url"]

        first = plugin.auth()
        second = plugin.auth()

        self.assertTrue(first["success"])
        self.assertGreaterEqual(len(first["state"]), 32)
        self.assertNotEqual(first["state"], second["state"])
        self.assertEqual(first["auth_url"], "first-url")
        auth_manager.get_authorize_url.assert_any_call(state=first["state"])
        auth_manager.get_authorize_url.assert_any_call(state=second["state"])

    def test_configure_uses_configured_protocol_in_redirect_uri(self):
        """
        Note this test is inaccurate and should change when spotify plugin is moved to
        a plugins repo
        :return:
        """
        with patch("smplfrm.plugins.spotify.spotify.SpotifyOAuth") as oauth_class:
            SpotifyPlugin().configure()

        self.assertEqual(
            oauth_class.call_args.kwargs["redirect_uri"],
            "Http://localhost:8321/api/v1/plugins/spotify/callback",
        )


class TestSpotifyTokenRecovery(SpotifyPluginTestCase):
    @patch("smplfrm.plugins.spotify.spotify.Spotify")
    def test_no_cached_token_requires_authorization_without_api_call(
        self, spotify_class
    ):
        plugin, _ = self.build_plugin()
        plugin.cache_manager.get_cached_token.return_value = None

        result = plugin.get_now_playing()

        self.assertEqual(
            result,
            {"success": False, "error": "authorization_required"},
        )
        spotify_class.assert_not_called()

    @patch("smplfrm.plugins.spotify.spotify.Spotify")
    def test_invalid_grant_clears_cache_and_requires_reauthorization(
        self, spotify_class
    ):
        plugin, _ = self.build_plugin()
        plugin.cache_manager.get_cached_token.return_value = {
            "access_token": "expired",
            "refresh_token": "expired-refresh",
        }
        spotify_class.return_value.current_user_playing_track.side_effect = (
            SpotifyOauthError(
                "refresh failed",
                error="invalid_grant",
                error_description="Refresh token expired",
            )
        )

        result = plugin.get_now_playing()

        self.assertEqual(result, {"success": False, "error": "reauth_required"})
        plugin.cache_manager.clear_cached_token.assert_called_once_with()

    @patch("smplfrm.plugins.spotify.spotify.Spotify")
    def test_other_oauth_errors_do_not_clear_cache(self, spotify_class):
        plugin, _ = self.build_plugin()
        plugin.cache_manager.get_cached_token.return_value = {
            "access_token": "token",
            "refresh_token": "refresh",
        }
        spotify_class.return_value.current_user_playing_track.side_effect = (
            SpotifyOauthError("bad client", error="invalid_client")
        )

        result = plugin.get_now_playing()

        self.assertEqual(result, {"success": False})
        plugin.cache_manager.clear_cached_token.assert_not_called()

    def test_callback_bypasses_cached_token(self):
        plugin, auth_manager = self.build_plugin()

        result = plugin.callback("new-code")

        self.assertEqual(result, {"success": True})
        auth_manager.get_access_token.assert_called_once_with(
            "new-code", check_cache=False
        )

    def test_callback_invalid_grant_clears_cache_and_requires_reauthorization(self):
        plugin, auth_manager = self.build_plugin()
        auth_manager.get_access_token.side_effect = SpotifyOauthError(
            "INVALID_GRANT: Authorization code expired"
        )

        result = plugin.callback("expired-code")

        self.assertEqual(result, {"success": False, "error": "reauth_required"})
        plugin.cache_manager.clear_cached_token.assert_called_once_with()

    def test_callback_non_expiration_errors_preserve_cached_credentials(self):
        errors = (
            SpotifyOauthError("bad client", error="invalid_client"),
            RuntimeError("temporary code exchange failure"),
        )

        # Configuration and transient failures may recover; only invalid_grant
        # proves that cached credentials are unusable and should be deleted.
        for error in errors:
            with self.subTest(error=type(error).__name__):
                plugin, auth_manager = self.build_plugin()
                auth_manager.get_access_token.side_effect = error

                result = plugin.callback("authorization-code")

                self.assertEqual(result, {"success": False})
                plugin.cache_manager.clear_cached_token.assert_not_called()


class TestSpotifyDisabledOperations(TestCase):
    def setUp(self):
        from smplfrm.services.config_service import ConfigService

        config = ConfigService().load_config()
        config.plugins = []
        config.save()
        self.plugin = SpotifyPlugin()

    def test_disabled_plugin_operations_return_explicit_failures(self):
        # Disabled plugins must not expose a fake authorization target or
        # attempt token and playback operations.
        self.assertEqual(self.plugin.auth(), {"success": False})
        self.assertEqual(self.plugin.get_now_playing(), {"success": False})
        self.assertEqual(
            self.plugin.callback("authorization-code"),
            {"success": False},
        )


class TestSpotifyCacheHandler(TestCase):
    def test_clear_cached_token_deletes_cache_file(self):
        with TemporaryDirectory() as directory:
            cache_path = Path(directory) / "spotify-token-cache"
            handler = SpotifyCacheHandler()
            handler.cache_path = str(cache_path)
            handler.save_token_to_cache(
                {"access_token": "token", "refresh_token": "refresh"}
            )
            self.assertTrue(cache_path.exists())

            handler.clear_cached_token()

            self.assertFalse(cache_path.exists())
            self.assertIsNone(handler.get_cached_token())
