"""Themes API views.

Provides a read-only JSON:API collection of the registered themes. The
catalogue is static server knowledge generated from the theme registry, so
there is nothing to write: no create, update, or delete, and no detail route.
"""

from rest_framework import viewsets
from rest_framework.request import Request

from smplfrm.jsonapi import jsonapi_exception_handler, StrictQueryMixin
from smplfrm.jsonapi.exceptions import InvalidQueryParameterError
from smplfrm.themes import get_all_themes
from smplfrm.views.serializers.v1.theme_serializer import ThemeSerializer


class ThemeViewSet(StrictQueryMixin, viewsets.GenericViewSet):
    """JSON:API Themes endpoint.

    Supports:
    - GET /themes - list all registered themes (paginated)

    No queryset and no detail action: the router emits the collection route
    only, so every other method and the detail path answer 405/404 without
    hand-written guards. GenericViewSet supplies pagination machinery
    (paginate_queryset, get_paginated_response) without requiring a queryset,
    since list() builds its page directly from the theme registry.
    """

    resource_name = "themes"
    allowed_query_params = {"page[number]"}

    def get_exception_handler(self):
        return jsonapi_exception_handler

    def _validate_query_params(self, request: Request) -> None:
        """Reject any filter[...] parameter.

        StrictQueryMixin's default behaviour is to pass filter[field] through
        unless allowed_filters restricts it, which suits routes with at least
        one approved filter. The themes catalogue approves none: there is
        nothing in it to filter on, so every filter[...] parameter is
        rejected the same way an unknown parameter would be.
        """
        for param in request.query_params:
            if param.startswith("filter[") and param.endswith("]"):
                raise InvalidQueryParameterError(param)
        super()._validate_query_params(request)

    def list(self, request, *args, **kwargs):
        themes = get_all_themes()
        page = self.paginate_queryset(themes)
        serializer = ThemeSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
