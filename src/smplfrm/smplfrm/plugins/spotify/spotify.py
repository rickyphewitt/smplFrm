import requests
from spotipy.oauth2 import SpotifyOAuth
from spotipy import Spotify, CacheFileHandler
from django.conf import settings

import logging

logger = logging.getLogger(__name__)


class SpotifyCacheHandler(CacheFileHandler):
    """
    @ToDo implement better caching, waiting on v3 of spotipy
    or if I get impatient, for now this saves things in .cache
    """

    def __init__(self):
        super().__init__(cache_path=None, username=None, encoder_cls=None)


class SpotifyPlugin(object):

    def __init__(self):
        self.enabled = settings.SMPL_FRM_PLUGINS_SPOTIFY_ENABLED
        if not self.enabled:
            return
        self.client_id = settings.SMPL_FRM_PLUGINS_SPOTIFY_CLIENT_ID
        self.client_secret = settings.SMPL_FRM_PLUGINS_SPOTIFY_CLIENT_SECRET
        self.redirect_uri = settings.SMPL_FRM_PLUGINS_SPOTIFY_REDIRECT_URI

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
        self.sp = None

    def auth(self):

        auth_url = {"auth_url": "http://not.enabled"}
        if not self.__is_enabled:
            return auth_url

        auth_url = self.auth_manager.get_authorize_url()
        return {"auth_url": auth_url}

    def get_now_playing(self):
        """
        Get Now Playing Song
        :return:
        """

        now_playing = {"success": False}

        if not self.__is_enabled:
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
        """
        Save code into auth manager
        :param code:
        :return:
        """

        callback_response = {"success": False}

        if not self.__is_enabled:
            return callback_response

        try:
            self.auth_manager.get_access_token(code)
            callback_response["success"] = True
        except Exception as e:
            logger.error(f"Failed to exchange code: {str(e)}")

        return callback_response

    def __is_enabled(self):
        if not self.enabled:
            logger.warning("Spotify Plugin Not Enabled")

        return self.enabled
