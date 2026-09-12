"""Image Metadata API views.

Provides JSON:API endpoints for image metadata list and detail.
Image metadata is read-only through the API.
"""

import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework_json_api.pagination import JsonApiPageNumberPagination

from smplfrm.jsonapi import JsonApiRenderer, JsonApiParser, jsonapi_exception_handler
from smplfrm.models import ImageMetadata
from smplfrm.services.image_metadata_service import ImageMetadataService
from smplfrm.views.serializers.v1.image_metadata_serializer import (
    ImageMetadataSerializer,
)

logger = logging.getLogger(__name__)


class ImageMetadataPagination(JsonApiPageNumberPagination):
    """JSON:API pagination for image metadata with page[number]."""

    page_size = 5
    max_page_size = 100


class ImagesMetadata(viewsets.ModelViewSet):
    """JSON:API Image Metadata endpoint.

    Supports:
    - GET /images_metadata - list all metadata (paginated)
    - GET /images_metadata?filter[image]={external_id} - filter by image
    - GET /images_metadata/{external_id} - metadata detail

    Forbidden:
    - POST (create)
    - PUT (update)
    - PATCH (partial update)
    - DELETE (destroy)

    Security:
    - Returns 403 for non-existent resources to prevent enumeration attacks
    - exif data is never exposed in responses
    """

    queryset = (
        ImageMetadata.objects.filter(deleted=False)
        .select_related("image")
        .order_by("-created")
    )
    serializer_class = ImageMetadataSerializer
    renderer_classes = [JsonApiRenderer]
    parser_classes = [JsonApiParser]
    pagination_class = ImageMetadataPagination
    lookup_field = "external_id"
    resource_name = "image_metadata"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ImageMetadataService()

    def get_exception_handler(self):
        return jsonapi_exception_handler

    def get_queryset(self):
        """Filter by image external_id if filter[image] provided.

        Annotates image_external_id to avoid fetching full image objects.
        """
        queryset = super().get_queryset()

        image_external_id = self.request.query_params.get("filter[image]")
        if image_external_id is not None:
            queryset = queryset.filter(image__external_id=image_external_id)

        return queryset

    def get_object(self):
        """Return 403 instead of 404 to prevent resource enumeration."""
        try:
            return super().get_object()
        except Http404:
            raise PermissionDenied("Access denied")

    def create(self, request, *args, **kwargs):
        """Create operation is not allowed."""
        return Response(
            {
                "errors": [
                    {
                        "status": "405",
                        "code": "method_not_allowed",
                        "detail": "Image metadata creation is not supported",
                    }
                ]
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def update(self, request, *args, **kwargs):
        """Update operation is not allowed."""
        return Response(
            {
                "errors": [
                    {
                        "status": "405",
                        "code": "method_not_allowed",
                        "detail": "Image metadata update is not supported",
                    }
                ]
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        """Partial update operation is not allowed."""
        return Response(
            {
                "errors": [
                    {
                        "status": "405",
                        "code": "method_not_allowed",
                        "detail": "Image metadata partial update is not supported",
                    }
                ]
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        """Delete operation is not allowed."""
        return Response(
            {
                "errors": [
                    {
                        "status": "405",
                        "code": "method_not_allowed",
                        "detail": "Image metadata deletion is not supported",
                    }
                ]
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
