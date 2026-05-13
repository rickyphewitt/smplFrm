import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def sanitized_exception_handler(exc, context):
    """
    Custom DRF exception handler that sanitizes unhandled exceptions.

    Delegates to DRF's default handler for known exceptions (validation errors,
    authentication failures, permission denied, throttled, not found, etc.).
    For any unhandled exception that DRF doesn't recognize, returns a generic
    500 response and logs the original error server-side.
    """
    response = drf_exception_handler(exc, context)

    if response is not None:
        # DRF handled it (400, 401, 403, 404, 405, 429, etc.)
        return response

    # Unhandled exception — log it and return a generic 500
    logger.error(
        "Unhandled exception in %s: %s",
        context.get("view", "unknown view"),
        exc,
        exc_info=True,
    )
    return Response(
        {"detail": "An internal error occurred"},
        status=500,
    )
