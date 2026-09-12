"""Image API views.

Provides JSON:API endpoints for image list, detail, and next selection.
The display endpoint is exempt from JSON:API (returns binary image/jpeg).

Create, update, and delete are forbidden.
"""

import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from smplfrm.jsonapi import jsonapi_exception_handler
from smplfrm.models import Image
from smplfrm.services import CacheService, ImageService, ImageManipulationService
from smplfrm.tasks import cache_images_task
from smplfrm.views.serializers.v1.image_serializer import ImageSerializer

logger = logging.getLogger(__name__)

DEFAULT_WIDTH = "100"
DEFAULT_HEIGHT = "100"
NEXT_IMAGE_COUNT = 5


class Images(viewsets.ModelViewSet):
    """JSON:API Image endpoint.

    Supports:
    - GET /images - list all images (paginated)
    - GET /images/{external_id} - image detail
    - GET /images/{external_id}/display - binary image (EXEMPT from JSON:API)
    - GET /images/next - next image for display cycle

    Forbidden:
    - POST (create)
    - PUT (update)
    - PATCH (partial update)
    - DELETE (destroy)

    Security:
    - Returns 403 for non-existent resources to prevent enumeration attacks
    - file_path is never exposed in responses
    """

    queryset = Image.objects.filter(deleted=False).order_by("-created")
    serializer_class = ImageSerializer
    lookup_field = "external_id"
    resource_name = "images"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ImageService()
        self.image_manipulation = ImageManipulationService()
        self.cache_service = CacheService()

    def get_exception_handler(self):
        return jsonapi_exception_handler

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
                        "detail": "Image creation is not supported",
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
                        "detail": "Image update is not supported",
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
                        "detail": "Image partial update is not supported",
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
                        "detail": "Image deletion is not supported",
                    }
                ]
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(methods=["get"], detail=True, url_path="display")
    def display_image(self, request, external_id=None):
        """Display an image with optional resizing.

        This endpoint is EXEMPT from JSON:API - returns binary image/jpeg.

        Args:
            request: HTTP request with optional width/height parameters
            external_id: External ID of the image

        Returns:
            HTTP response with image data or 404 if not found
        """
        image = self.service.read(ext_id=external_id)
        if not image:
            return HttpResponse(status=404)

        width = request.GET.get("width", DEFAULT_WIDTH)
        height = request.GET.get("height", DEFAULT_HEIGHT)

        result = ImageManipulationService.validate_dimensions(width, height)
        if result[0] is None:
            return HttpResponse(
                content_type="application/json",
                content=f'{{"error": "{result[1]}"}}',
                status=400,
            )
        validated_width, validated_height = result

        cache_key = self.cache_service.get_image_cache_key(
            image.external_id, height, width
        )
        cached_image = self.cache_service.read(cache_key=cache_key)

        if cached_image is None:
            try:
                cached_image = self.image_manipulation.display(
                    image, validated_height, validated_width
                )
            except FileNotFoundError:
                return HttpResponse(status=404)

            self.cache_service.upsert(cache_key=cache_key, cache_data=cached_image)

        self.service.increment_view_count(image)

        response = HttpResponse(status=200, headers={"Content-type": "image/jpeg"})
        response.write(cached_image.tobytes())
        return response

    @action(methods=["get"], detail=False, url_path="next")
    def next_image(self, request):
        """Get the next image to display and preload upcoming images.

        Args:
            request: HTTP request with optional width/height parameters

        Returns:
            JSON:API formatted image resource
        """
        width = request.GET.get("width", DEFAULT_WIDTH)
        height = request.GET.get("height", DEFAULT_HEIGHT)

        result = ImageManipulationService.validate_dimensions(width, height)
        if result[0] is None:
            return Response(
                {
                    "errors": [
                        {
                            "status": "400",
                            "code": "invalid_dimensions",
                            "detail": result[1],
                        }
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        images = self.service.get_next()[:NEXT_IMAGE_COUNT]
        if not images:
            return Response(
                {
                    "errors": [
                        {
                            "status": "404",
                            "code": "not_found",
                            "detail": "No images available",
                        }
                    ]
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        image = images[0]
        serializer = self.get_serializer(image)

        cache_image_list = [img.external_id for img in images]
        cache_images_task.delay(cache_image_list, height, width)

        return Response(serializer.data)

    def perform_create(self, serializer):
        """Create image record from validated data."""
        self.service.create(serializer.validated_data)
