"""JSON:API exception handling for smplFrm.

Provides custom exceptions and an exception handler that produces
JSON:API compliant error responses with the errors array format.
"""

import logging
from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class JsonApiError(APIException):
    """Base class for JSON:API errors.

    Subclass this for domain-specific errors with stable error codes.
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_code = "error"
    default_detail = "An error occurred"

    def __init__(self, detail: str = None, code: str = None):
        super().__init__(detail=detail or self.default_detail)
        self.code = code or self.default_code


class WeatherUnavailableError(JsonApiError):
    """Raised when weather data cannot be retrieved."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "weather_unavailable"
    default_detail = "Unable to retrieve weather data"


class InvalidQueryParameterError(JsonApiError):
    """Raised when an invalid query parameter is detected."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "invalid_query_parameter"
    default_detail = "Invalid query parameter"

    def __init__(self, param_name: str = None):
        detail = self.default_detail
        if param_name:
            detail = f"Invalid query parameter: {param_name}"
        super().__init__(detail=detail)


class InternalError(JsonApiError):
    """Generic internal error for unexpected failures."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_code = "internal_error"
    default_detail = "An unexpected error occurred"


def format_jsonapi_error(
    status_code: int,
    code: str,
    detail: str,
    source: dict = None,
) -> dict:
    """Format a single error object per JSON:API spec.

    Args:
        status_code: HTTP status code (rendered as string per spec).
        code: Stable application-specific error code.
        detail: Human-readable error description.
        source: Optional dict with pointer or parameter field.

    Returns:
        Dict conforming to JSON:API error object structure.
    """
    error = {
        "status": str(status_code),
        "code": code,
        "detail": detail,
    }
    if source:
        error["source"] = source
    return error


def format_jsonapi_errors_response(errors: list[dict]) -> dict:
    """Format a top-level JSON:API errors response.

    Args:
        errors: List of error objects from format_jsonapi_error.

    Returns:
        Dict with top-level 'errors' key.
    """
    return {"errors": errors}


def jsonapi_exception_handler(exc: Exception, context: dict) -> Response | None:
    """Exception handler that produces JSON:API error responses.

    This handler:
    1. Handles JsonApiError subclasses with their defined codes.
    2. Delegates standard DRF exceptions to DRF's handler, then reformats.
    3. Catches unhandled exceptions, logs them, and returns generic 500.

    The response Content-Type is set by the renderer (JsonApiRenderer).
    """
    # Handle our custom JSON:API errors
    if isinstance(exc, JsonApiError):
        error = format_jsonapi_error(
            status_code=exc.status_code,
            code=exc.code,
            detail=str(exc.detail),
        )
        return Response(
            format_jsonapi_errors_response([error]),
            status=exc.status_code,
        )

    # Delegate to DRF's handler for standard exceptions
    response = drf_exception_handler(exc, context)

    if response is not None:
        # Reformat DRF's response to JSON:API errors array
        errors = _convert_drf_response_to_jsonapi_errors(response)
        response.data = format_jsonapi_errors_response(errors)
        return response

    # Unhandled exception — log it and return generic 500
    logger.error(
        "Unhandled exception in %s: %s",
        context.get("view", "unknown view"),
        exc,
        exc_info=True,
    )
    error = format_jsonapi_error(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        detail="An unexpected error occurred",
    )
    return Response(
        format_jsonapi_errors_response([error]),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _convert_drf_response_to_jsonapi_errors(response: Response) -> list[dict]:
    """Convert a DRF error response to JSON:API errors array.

    DRF can return errors in various formats:
    - {"detail": "..."} for simple errors
    - {"field": ["error1", "error2"]} for validation errors
    - {"non_field_errors": ["..."]} for form-level errors
    """
    errors = []
    data = response.data

    if isinstance(data, dict):
        if "detail" in data:
            # Simple error like PermissionDenied, NotFound, etc.
            errors.append(
                format_jsonapi_error(
                    status_code=response.status_code,
                    code=_status_to_code(response.status_code),
                    detail=str(data["detail"]),
                )
            )
        else:
            # Validation errors: {"field": ["msg1", "msg2"]}
            for field, messages in data.items():
                if isinstance(messages, list):
                    for msg in messages:
                        errors.append(
                            format_jsonapi_error(
                                status_code=response.status_code,
                                code="validation_error",
                                detail=str(msg),
                                source={"pointer": f"/data/attributes/{field}"},
                            )
                        )
                else:
                    errors.append(
                        format_jsonapi_error(
                            status_code=response.status_code,
                            code="validation_error",
                            detail=str(messages),
                            source={"pointer": f"/data/attributes/{field}"},
                        )
                    )
    elif isinstance(data, list):
        # List of error messages
        for msg in data:
            errors.append(
                format_jsonapi_error(
                    status_code=response.status_code,
                    code=_status_to_code(response.status_code),
                    detail=str(msg),
                )
            )
    else:
        # Fallback for unexpected formats
        errors.append(
            format_jsonapi_error(
                status_code=response.status_code,
                code=_status_to_code(response.status_code),
                detail=str(data),
            )
        )

    return (
        errors
        if errors
        else [
            format_jsonapi_error(
                status_code=response.status_code,
                code=_status_to_code(response.status_code),
                detail="An error occurred",
            )
        ]
    )


def _status_to_code(status_code: int) -> str:
    """Map HTTP status codes to stable error codes."""
    code_map = {
        400: "bad_request",
        401: "authentication_required",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        406: "not_acceptable",
        415: "unsupported_media_type",
        429: "rate_limited",
        500: "internal_error",
    }
    return code_map.get(status_code, "error")
