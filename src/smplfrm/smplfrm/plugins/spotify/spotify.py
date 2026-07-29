import logging
import secrets
from pathlib import Path

from django.conf import settings
from spotipy import CacheFileHandler, Spotify
from spotipy.exceptions import SpotifyOauthError
from spotipy.oauth2 import SpotifyOAuth

from smplfrm.plugins.base import BasePlugin

logger = logging.getLogger(__name__)

OAUTH_STATE_BYTES = 32


def _is_invalid_grant(error: SpotifyOauthError) -> bool:
    """Return whether Spotify rejected an OAuth grant as unusable."""
    error_code = str(getattr(error, "error", "") or "").casefold()
    return error_code == "invalid_grant" or "invalid_grant" in str(error).casefold()


class SpotifyCacheHandler(CacheFileHandler):
    """File-backed Spotify token cache with explicit credential removal."""

    def __init__(self):
        super().__init__(cache_path=None, username=None, encoder_cls=None)

    def clear_cached_token(self) -> None:
        """Remove cached credentials after a terminal OAuth refresh failure."""
        try:
            Path(self.cache_path).unlink()
        except FileNotFoundError:
            return
        except OSError:
            logger.exception("Could not delete the Spotify token cache")
            # Erase the credentials even when the containing directory does not
            # permit unlinking. Spotipy reads JSON null back as no cached token.
            self.save_token_to_cache(None)


class SpotifyPlugin(BasePlugin):
    """Spotify integration plugin for displaying now playing information."""

    def __init__(self):
        super().__init__(name="spotify", description="Now playing display")
        self.sp = None
        self._ready = False

    def get_settings_schema(self):
        return [
            {"key": "client_id", "label": "Client ID", "type": "password"},
            {"key": "client_secret", "label": "Client Secret", "type": "password"},
        ]

    def get_viewset(self):
        from smplfrm.views.api.plugins.v1.spotify.spotify_view import SpotifyView

        return SpotifyView

    def configure(self):
        """Load settings from DB and set up Spotify auth."""
        super().configure()

        if not self.is_enabled():
            return

        plugin_settings = self.get_plugin_settings()
        self.client_id = plugin_settings.get("client_id", "")
        self.client_secret = plugin_settings.get("client_secret", "")
        self.redirect_uri = (
            f"Http://{settings.SMPL_FRM_HOST}:{settings.SMPL_FRM_EXTERNAL_PORT}"
            f"/api/v1/plugins/spotify/callback"
        )

        if not self.client_id or not self.client_secret:
            logger.warning("Client Id or Secret Not Defined, Disabling Spotify")
            return

        self.cache_manager = SpotifyCacheHandler()
        self.auth_manager = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope="user-read-currently-playing",
            cache_handler=self.cache_manager,
        )
        self._ready = True

    @property
    def is_ready(self):
        """Check if Spotify plugin is enabled and configured."""
        self._ensure_configured()
        if not self._ready:
            logger.warning("Spotify Plugin Not Enabled")
        return self._ready

    def auth(self):
        """Create a state-bound Spotify authorization URL."""
        if not self.is_ready:
            return {"success": False}

        state = secrets.token_urlsafe(OAUTH_STATE_BYTES)
        return {
            "success": True,
            "state": state,
            "auth_url": self.auth_manager.get_authorize_url(state=state),
        }

    def get_now_playing(self):
        """Get currently playing track information."""
        now_playing = {"success": False}
        if not self.is_ready:
            return now_playing

        if not self.cache_manager.get_cached_token():
            return {"success": False, "error": "authorization_required"}

        try:
            self.sp = Spotify(auth_manager=self.auth_manager)
            results = self.sp.current_user_playing_track()

            if results.get("currently_playing_type") == "track":
                artist = results.get("item").get("artists")[0]["name"]
                song = results.get("item").get("name")
            elif results.get("currently_playing_type") == "episode":
                artist = "Awesome"
                song = "Podcast"
            else:
                artist = "Unsupported Type"
                song = results.get("currently_playing_type")

            now_playing["artist"] = artist
            now_playing["song"] = song
            now_playing["success"] = True
        except SpotifyOauthError as error:
            if _is_invalid_grant(error):
                self.cache_manager.clear_cached_token()
                logger.warning(
                    "Spotify refresh token is no longer valid; "
                    "reauthorization is required"
                )
                return {"success": False, "error": "reauth_required"}

            logger.error("Spotify OAuth request failed", exc_info=True)
        except Exception:
            logger.error("Failed to get now playing song", exc_info=True)
        return now_playing

    def callback(self, code):
        """Exchange a validated authorization code for fresh tokens."""
        callback_response = {"success": False}
        if not self.is_ready:
            return callback_response

        try:
            self.auth_manager.get_access_token(code, check_cache=False)
            callback_response["success"] = True
        except SpotifyOauthError as error:
            if _is_invalid_grant(error):
                self.cache_manager.clear_cached_token()
                logger.warning(
                    "Spotify authorization grant is no longer valid; "
                    "reauthorization is required"
                )
                callback_response["error"] = "reauth_required"
                return callback_response

            logger.error("Spotify authorization code exchange failed", exc_info=True)
        except Exception:
            logger.error("Unexpected Spotify code exchange failure", exc_info=True)
        return callback_response
