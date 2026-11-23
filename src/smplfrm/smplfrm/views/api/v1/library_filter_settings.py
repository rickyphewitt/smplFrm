"""Library filter settings API views.

A single settings row turns library filtering on or off. It is created by a
migration and addressed by its own id; it can be read and replaced with PUT
but never created or deleted.
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import mixins, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from smplfrm.jsonapi import jsonapi_exception_handler, StrictQueryMixin
from smplfrm.jsonapi.exceptions import InvalidQueryParameterError
from smplfrm.services import LibraryFilterSettingsService
from smplfrm.views.serializers.v1.library_filter_settings_serializer import (
    LibraryFilterSettingsSerializer,
)


class LibraryFilterSettingsViewSet(
    StrictQueryMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """JSON:API library filter settings endpoint.

    Supports:
    - GET /library_filter_settings - list (always one row)
    - GET /library_filter_settings/{external_id} - detail
    - PUT /library_filter_settings/{external_id} - set ``enabled``

    POST, PATCH, and DELETE are not routed and answer 405.

    Security:
    - Returns 403 for unknown ids to prevent enumeration
    """

    serializer_class = LibraryFilterSettingsSerializer
    lookup_field = "external_id"
    resource_name = "library_filter_settings"
    allowed_query_params = {"page[number]"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = LibraryFilterSettingsService()

    def get_exception_handler(self):
        return jsonapi_exception_handler

    def _validate_query_params(self, request: Request) -> None:
        """Reject every filter[...] parameter; this resource has none."""
        for param in request.query_params:
            if param.startswith("filter[") and param.endswith("]"):
                raise InvalidQueryParameterError(param)
        super()._validate_query_params(request)

    def get_queryset(self):
        return self.service.list()

    def get_object(self):
        """Return 403 instead of 404 to prevent resource enumeration."""
        try:
            return super().get_object()
        except Http404:
            raise PermissionDenied("Access denied")

    def update(self, request, *args, **kwargs):
        settings = self.get_object()
        serializer = self.get_serializer(settings, data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = self.service.set_enabled(
            settings, serializer.validated_data["enabled"]
        )
        return Response(self.get_serializer(updated).data)
