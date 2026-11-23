"""Tags API views.

Provides a read-only JSON:API collection of the tags found in image metadata.
Tags are created and updated only by the library scan, so the router emits
GET routes only; every other method answers 405 through the shared JSON:API
exception handler.
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import viewsets

from smplfrm.jsonapi import jsonapi_exception_handler, StrictQueryMixin
from smplfrm.services import TagService
from smplfrm.views.serializers.v1.tag_serializer import TagSerializer


class TagViewSet(StrictQueryMixin, viewsets.ReadOnlyModelViewSet):
    """JSON:API Tags endpoint.

    Supports:
    - GET /tags - list non-deleted tags (paginated, ordered by value)
    - GET /tags?filter[value]={text} - exact match on the canonical form
    - GET /tags/{external_id} - tag detail

    Security:
    - Returns 403 for unknown or deleted tags to prevent enumeration
    """

    serializer_class = TagSerializer
    lookup_field = "external_id"
    resource_name = "tags"

    allowed_query_params = {"page[number]"}
    allowed_filters = {"value"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = TagService()

    def get_exception_handler(self):
        return jsonapi_exception_handler

    def get_queryset(self):
        return self.service.list_with_usage(
            value=self.request.query_params.get("filter[value]")
        )

    def get_object(self):
        """Return 403 instead of 404 to prevent resource enumeration."""
        try:
            return super().get_object()
        except Http404:
            raise PermissionDenied("Access denied")
