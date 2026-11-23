"""Library filter API views.

A library filter is a named set of rules. At most one filter is active.
Rules are managed through /library_filter_rules; a filter lists its live rule
ids as a read-only relationship.
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from smplfrm.jsonapi import jsonapi_exception_handler, StrictQueryMixin
from smplfrm.jsonapi.exceptions import InvalidQueryParameterError
from smplfrm.services import LibraryFilterService
from smplfrm.services.library_filter.exceptions import LibraryFilterError
from smplfrm.views.api.v1.library_filter_errors import to_api_error
from smplfrm.views.serializers.v1.library_filter_serializer import (
    LibraryFilterSerializer,
)

_BOOLEAN_FILTER_VALUES = {"true": True, "false": False}


class LibraryFilterViewSet(
    StrictQueryMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """JSON:API library filter endpoint.

    Supports:
    - GET /library_filters - list live filters (paginated, ordered by name)
    - GET /library_filters?filter[is_active]=true|false
    - GET /library_filters/{external_id} - detail
    - POST /library_filters - create
    - PUT /library_filters/{external_id} - full replacement; omitted
      description becomes "" and omitted is_active becomes false
    - DELETE /library_filters/{external_id} - soft delete with its rules

    PATCH is not routed and answers 405.

    Security:
    - Returns 403 for unknown or deleted ids to prevent enumeration
    """

    serializer_class = LibraryFilterSerializer
    lookup_field = "external_id"
    resource_name = "library_filters"
    allowed_query_params = {"page[number]"}
    allowed_filters = {"is_active"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = LibraryFilterService()

    def get_exception_handler(self):
        return jsonapi_exception_handler

    def get_queryset(self):
        return self.service.list_for_api(is_active=self._is_active_filter())

    def _is_active_filter(self):
        param = "filter[is_active]"
        raw = self.request.query_params.get(param)
        if raw is None:
            return None
        if raw not in _BOOLEAN_FILTER_VALUES:
            raise InvalidQueryParameterError(param)
        return _BOOLEAN_FILTER_VALUES[raw]

    def get_object(self):
        """Return 403 instead of 404 to prevent resource enumeration."""
        try:
            return super().get_object()
        except Http404:
            raise PermissionDenied("Access denied")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            library_filter = self.service.create(serializer.validated_data)
        except LibraryFilterError as e:
            raise to_api_error(e) from e
        return Response(
            self.get_serializer(library_filter).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        library_filter = self.get_object()
        serializer = self.get_serializer(library_filter, data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = self.service.replace(library_filter, serializer.validated_data)
        except LibraryFilterError as e:
            raise to_api_error(e) from e
        return Response(self.get_serializer(updated).data)

    def destroy(self, request, *args, **kwargs):
        library_filter = self.get_object()
        self.service.delete(library_filter.external_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
