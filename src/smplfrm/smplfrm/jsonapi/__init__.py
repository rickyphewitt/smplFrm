"""Shared JSON:API infrastructure for smplFrm.

This module provides the building blocks for JSON:API compliance:
- Renderers and parsers with application/vnd.api+json media type
- Exception handling producing JSON:API errors array
- Strict query parameter validation
- Pagination with server-controlled page size
- Serializers for JSON:API resource documents

Usage in views:
    from smplfrm.jsonapi import (
        JsonApiParser,
        JsonApiRenderer,
        JsonApiPagination,
        StrictQueryMixin,
        JsonApiError,
        jsonapi_exception_handler,
    )
"""

from smplfrm.jsonapi.renderers import JsonApiRenderer
from smplfrm.jsonapi.parsers import JsonApiParser
from smplfrm.jsonapi.pagination import JsonApiPagination
from smplfrm.jsonapi.exceptions import (
    JsonApiError,
    WeatherUnavailableError,
    InvalidQueryParameterError,
    InternalError,
    jsonapi_exception_handler,
)
from smplfrm.jsonapi.query import StrictQueryMixin
from smplfrm.jsonapi.serializers import SECRET_MASK

__all__ = [
    "JsonApiRenderer",
    "JsonApiParser",
    "JsonApiPagination",
    "JsonApiError",
    "WeatherUnavailableError",
    "InvalidQueryParameterError",
    "InternalError",
    "jsonapi_exception_handler",
    "StrictQueryMixin",
    "SECRET_MASK",
]
