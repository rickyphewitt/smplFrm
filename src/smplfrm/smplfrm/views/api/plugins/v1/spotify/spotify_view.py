import logging
import secrets

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, render
from rest_framework import viewsets
from rest_framework.decorators import action

from smplfrm.plugins import SpotifyPlugin

logger = logging.getLogger(__name__)

SPOTIFY_OAUTH_STATE_SESSION_KEY = "spotify_oauth_state"


class SpotifyView(viewsets.ViewSet):

    @action(methods=["get"], detail=False, url_path="auth")
    def auth(self, request, **kwargs):
        try:
            auth_result = SpotifyPlugin().auth()
        except Exception:
            logger.error("Failed to create Spotify authorization URL", exc_info=True)
            return JsonResponse({"error": "spotify_unavailable"}, status=500)

        if not auth_result.get("success"):
            return JsonResponse({"error": "spotify_not_configured"}, status=412)

        request.session[SPOTIFY_OAUTH_STATE_SESSION_KEY] = auth_result["state"]
        return JsonResponse({"auth_url": auth_result["auth_url"]})

    @action(methods=["get"], detail=False, url_path="now_playing")
    def get_now_playing(self, request, **kwargs):
        try:
            now_playing = SpotifyPlugin().get_now_playing()
        except Exception:
            logger.error("Failed to retrieve Spotify now-playing data", exc_info=True)
            return JsonResponse({"error": "spotify_unavailable"}, status=500)

        error = now_playing.get("error")
        if error in {"authorization_required", "reauth_required"}:
            reason = "expired" if error == "reauth_required" else "missing"
            return JsonResponse(
                {
                    "error": "spotify_authorization_required",
                    "reason": reason,
                },
                status=401,
            )

        if not now_playing.get("success"):
            return JsonResponse({"error": "spotify_unavailable"}, status=412)

        return JsonResponse(
            {
                "artist": now_playing.get("artist"),
                "song": now_playing.get("song"),
            }
        )

    @action(methods=["get"], detail=False, url_path="callback")
    def callback(self, request, **kwargs):
        callback_state = request.GET.get("state")
        stored_state = request.session.get(SPOTIFY_OAUTH_STATE_SESSION_KEY)
        valid_state = (
            isinstance(callback_state, str)
            and isinstance(stored_state, str)
            and bool(callback_state)
            and bool(stored_state)
            and secrets.compare_digest(callback_state, stored_state)
        )

        if not valid_state:
            return render(
                request,
                "spotify_callback_error.html",
                status=403,
            )

        # A matching state is single-use, even if the later code exchange fails.
        request.session.pop(SPOTIFY_OAUTH_STATE_SESSION_KEY, None)

        code = request.GET.get("code")
        if not code:
            return render(
                request,
                "spotify_callback_error.html",
                status=400,
            )

        try:
            callback_result = SpotifyPlugin().callback(code)
        except Exception:
            logger.error("Spotify callback failed", exc_info=True)
            return render(
                request,
                "spotify_callback_error.html",
                status=500,
            )

        if not callback_result.get("success"):
            return render(
                request,
                "spotify_callback_error.html",
                status=412,
            )

        return redirect(
            f"{settings.SMPL_FRM_PROTOCOL}{settings.SMPL_FRM_HOST}:"
            f"{settings.SMPL_FRM_EXTERNAL_PORT}"
        )
