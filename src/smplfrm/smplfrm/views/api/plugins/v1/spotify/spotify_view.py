import logging
import secrets

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, render
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from rest_framework.renderers import JSONRenderer as BaseJSONRenderer

from smplfrm.plugins import SpotifyPlugin
from smplfrm.views.api.plugins.v1.spotify.serializers import SpotifyStatusSerializer


class JsonApiPassthroughRenderer(BaseJSONRenderer):
    """JSON renderer that uses JSON:API media type without document wrapping.

    Use for endpoints that build their own JSON:API document structure.
    """

    media_type = "application/vnd.api+json"


logger = logging.getLogger(__name__)

SPOTIFY_OAUTH_STATE_SESSION_KEY = "spotify_oauth_state"


class SpotifyView(viewsets.ViewSet):

    def get_exception_handler(self):
        """Use consolidated JSON:API exception handler."""
        from smplfrm.jsonapi.exceptions import jsonapi_exception_handler

        return jsonapi_exception_handler

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

    @action(
        methods=["get"],
        detail=False,
        url_path="status",
        renderer_classes=[JsonApiPassthroughRenderer],
    )
    def status(self, request, **kwargs):
        """Get current Spotify playback status.

        Returns JSON:API formatted spotify_status resource with track relationship.
        """
        try:
            result = SpotifyPlugin().get_now_playing()
        except Exception:
            logger.error("Failed to retrieve Spotify status", exc_info=True)
            return Response(
                {
                    "errors": [
                        {
                            "status": "500",
                            "code": "spotify_unavailable",
                            "detail": "Failed to retrieve Spotify status",
                        }
                    ]
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        error = result.get("error")
        if error in {"authorization_required", "reauth_required"}:
            reason = "expired" if error == "reauth_required" else "missing"
            return Response(
                {
                    "errors": [
                        {
                            "status": "401",
                            "code": "spotify_authorization_required",
                            "detail": f"Spotify authorization {reason}",
                        }
                    ]
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not result.get("success"):
            return Response(
                {
                    "errors": [
                        {
                            "status": "412",
                            "code": "spotify_unavailable",
                            "detail": "Spotify plugin not configured",
                        }
                    ]
                },
                status=status.HTTP_412_PRECONDITION_FAILED,
            )

        serializer = SpotifyStatusSerializer()
        return Response(serializer.to_representation(result))

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
