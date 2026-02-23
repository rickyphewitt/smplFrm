import logging
from django.core.exceptions import PermissionDenied
from rest_framework.decorators import action
from django.http import HttpResponse
from rest_framework.response import Response

from smplfrm.models import Image
from smplfrm.views.serializers.v1.image_serializer import ImageSerializer

from rest_framework import viewsets

from smplfrm.services import CacheService, ImageService, ImageManipulationService
from smplfrm.tasks import cache_images_task

logger = logging.getLogger(__name__)

DEFAULT_WIDTH = "100"
DEFAULT_HEIGHT = "100"
NEXT_IMAGE_COUNT = 5


class Images(viewsets.ModelViewSet):
    """ViewSet for managing and displaying images."""

    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    lookup_field = "external_id"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ImageService()
        self.image_manipulation = ImageManipulationService()
        self.cache_service = CacheService()

    def create(self, request, *args, **kwargs):
        """Create operation is not allowed."""
        raise PermissionDenied()

    def update(self, request, *args, **kwargs):
        """Update operation is not allowed."""
        raise PermissionDenied()

    def destroy(self, request, *args, **kwargs):
        """Delete operation is not allowed."""
        raise PermissionDenied()

    @action(methods=["get"], detail=True, url_path="display")
    def display_image(self, request, external_id=None):
        """Display an image with optional resizing.

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

        cache_key = self.cache_service.get_image_cache_key(
            image.external_id, height, width
        )
        cached_image = self.cache_service.read(cache_key=cache_key)

        if cached_image is None:
            try:
                cached_image = self.image_manipulation.display(
                    image, int(height), int(width)
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
            Serialized image data
        """
        images = self.service.get_next()[:NEXT_IMAGE_COUNT]
        image = images[0]

        serializer = self.get_serializer(image)

        width = request.GET.get("width", DEFAULT_WIDTH)
        height = request.GET.get("height", DEFAULT_HEIGHT)

        cache_image_list = [img.external_id for img in images]
        cache_images_task.delay(cache_image_list, height, width)

        return Response(serializer.data)

    def perform_create(self, serializer):
        """Create image record from validated data."""
        self.service.create(serializer.validated_data)
