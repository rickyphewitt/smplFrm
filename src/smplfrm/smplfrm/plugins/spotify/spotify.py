import requests
from spotipy.oauth2 import SpotifyOAuth
from spotipy import Spotify, CacheFileHandler
from django.conf import settings

from smplfrm.plugins.base import BasePlugin

import logging

logger = logging.getLogger(__name__)


class SpotifyCacheHandler(CacheFileHandler):
    """
    @ToDo implement better caching, waiting on v3 of spotipy
    or if I get impatient, for now this saves things in .cache
    """

    def __init__(self):
        super().__init__(cache_path=None, username=None, encoder_cls=None)


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

        s = self.get_plugin_settings()
        self.client_id = s.get("client_id", "")
        self.client_secret = s.get("client_secret", "")
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
        """Get Spotify authorization URL."""
        if not self.is_ready:
            return {"auth_url": "http://not.enabled"}
        return {"auth_url": self.auth_manager.get_authorize_url()}

    def get_now_playing(self):
        """Get currently playing track information."""
        now_playing = {"success": False}
        if not self.is_ready:
            return now_playing

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
        except Exception as e:
            logger.error("Failed to get now playing song: %s", str(e))
        return now_playing

    def callback(self, code):
        """Exchange authorization code for access token."""
        callback_response = {"success": False}
        if not self.is_ready:
            return callback_response

        try:
            self.auth_manager.get_access_token(code)
            callback_response["success"] = True
        except Exception as e:
            logger.error(f"Failed to exchange code: {str(e)}")
        return callback_response
