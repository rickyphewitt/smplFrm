"""Shared JSON:API infrastructure for smplFrm.

This module provides the building blocks for JSON:API compliance:
- Renderers and parsers with application/vnd.api+json media type
- Exception handling producing JSON:API errors array
- Strict query parameter validation
- Serializers for JSON:API resource documents

Usage in views:
    from smplfrm.jsonapi import (
        JsonApiParser,
        StrictQueryMixin,
        JsonApiError,
    )
    from smplfrm.jsonapi.serializers import WeatherSerializer, PluginSerializer
"""

from smplfrm.jsonapi.renderers import JsonApiRenderer
from smplfrm.jsonapi.parsers import JsonApiParser
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
    "JsonApiError",
    "WeatherUnavailableError",
    "InvalidQueryParameterError",
    "InternalError",
    "jsonapi_exception_handler",
    "StrictQueryMixin",
    "SECRET_MASK",
]
