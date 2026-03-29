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
        self.enabled = False
        self.sp = None

        try:
            from smplfrm.services.plugin_service import PluginService
            from smplfrm.services.config_service import ConfigService

            config = ConfigService().load_config()
            if self.name not in config.plugins:
                return

            plugin_settings = PluginService().read_by_name(self.name).settings
        except Exception:
            return

        self.client_id = plugin_settings.get("client_id", "")
        self.client_secret = plugin_settings.get("client_secret", "")
        self.redirect_uri = (
            f"Http://{settings.SMPL_FRM_HOST}:{settings.SMPL_FRM_EXTERNAL_PORT}"
            f"/api/v1/plugins/spotify/callback"
        )

        # if we don't have the required config, set as disabled
        if not self.client_id or not self.client_secret or not self.redirect_uri:
            self.enabled = False
            logger.warning(
                "Client Id, Secret, or Redirect Uri Not Defined, Disabling Spotify"
            )
            return

        self.cache_manager = SpotifyCacheHandler()
        self.auth_manager = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope="user-read-currently-playing",
            cache_handler=self.cache_manager,
        )
        self.enabled = True
        self.sp = None

    @property
    def is_enabled(self):
        """Check if Spotify plugin is enabled."""
        if not self.enabled:
            logger.warning("Spotify Plugin Not Enabled")
        return self.enabled

    def auth(self):
        """Get Spotify authorization URL.

        Returns:
            Dictionary containing auth_url
        """
        auth_url = {"auth_url": "http://not.enabled"}
        if not self.is_enabled:
            return auth_url

        auth_url = self.auth_manager.get_authorize_url()
        return {"auth_url": auth_url}

    def get_now_playing(self):
        """Get currently playing track information.

        Returns:
            Dictionary with artist, song, and success status
        """
        now_playing = {"success": False}

        if not self.is_enabled:
            return now_playing

        try:
            self.sp = Spotify(auth_manager=self.auth_manager)
            results = self.sp.current_user_playing_track()

            if results.get("currently_playing_type") == "track":
                artist = results.get("item").get("artists")[0]["name"]
                song = results.get("item").get("name")
            elif results.get("currently_playing_type") == "episode":
                # currently doesn't support podcasts :/
                # https://developer.spotify.com/documentation/web-api/reference/get-recently-played
                artist = "Awesome"
                song = "Podcast"
            else:
                # returned an unsupported type, this indicates we may need to
                # support more types as the api evolves!
                artist = "Unsupported Type"
                song = results.get("currently_playing_type")

            now_playing["artist"] = artist
            now_playing["song"] = song
            now_playing["success"] = True
        except Exception as e:
            # if we get an error try and (re)auth
            logger.error("Failed to get now playing song: %s", str(e))
        return now_playing

    def callback(self, code):
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from Spotify

        Returns:
            Dictionary with success status
        """
        callback_response = {"success": False}

        if not self.is_enabled:
            return callback_response

        try:
            self.auth_manager.get_access_token(code)
            callback_response["success"] = True
        except Exception as e:
            logger.error(f"Failed to exchange code: {str(e)}")

        return callback_response
