"""Map library filter domain errors to JSON:API errors."""

from rest_framework.exceptions import APIException, PermissionDenied

from smplfrm.jsonapi.exceptions import BadRequestError
from smplfrm.services.library_filter.exceptions import (
    LibraryFilterError,
    LibraryFilterNotFound,
)


def to_api_error(exc: LibraryFilterError) -> APIException:
    """Return the API error to raise for a domain error.

    An unknown or deleted filter answers 403, the same as an unknown detail
    id, so callers cannot tell which filter ids exist. Every other domain
    error is a 400 carrying the error's stable code.
    """
    if isinstance(exc, LibraryFilterNotFound):
        return PermissionDenied("Access denied")
    return BadRequestError(detail=exc.detail, code=exc.code)
