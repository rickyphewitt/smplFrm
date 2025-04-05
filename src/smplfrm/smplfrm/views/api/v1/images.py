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

class Images(viewsets.ModelViewSet):

    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    lookup_field = "external_id"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ImageService()
        self.image_manipulation = ImageManipulationService()
        self.cache_service = CacheService()

    # for now only allow list and read
    def create(self, request, *args, **kwargs):
        raise PermissionDenied()

    def update(self, request, *args, **kwargs):
        raise PermissionDenied()

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied()

    # handle displaying an image
    @action(methods=['get'], detail=True, url_path="display")
    def display_image(self, request, external_id=None):
        image = self.service.read(ext_id=external_id)
        if image:
            # get w/h of caller
            width = request.GET.get('width', '100')
            height = request.GET.get('height', '100')

            cache_key = self.cache_service.get_image_cache_key(image.external_id, height, width)
            cached_image = self.cache_service.read(cache_key=cache_key)
            if cached_image is None:
                try:
                    cached_image = self.image_manipulation.display(image, int(height), int(width))
                except FileNotFoundError:
                    return HttpResponse(status=404)

                # cache image
                self.cache_service.upsert(cache_key=cache_key, cache_data=cached_image)

            # mark image as viewed
            self.service.increment_view_count(image)

            # send to client
            response = HttpResponse(status=200, headers={'Content-type': 'image/jpeg'})
            response.write(cached_image.tobytes())
            return response
        else:
            return HttpResponse(status=404)

    @action(methods=['get'], detail=False, url_path="next")
    def next_image(self, request):
        """

        :param request:
        :return:
        """

        # get next 5 images from db
        images = self.service.get_next()[:5]
        # grab the 1st image to be sent back
        image = images[0]

        serializer = self.get_serializer(image)

        # get w/h of caller
        width = request.GET.get('width', '100')
        height = request.GET.get('height', '100')

        cache_image_list = []
        for img in images:
            cache_image_list.append(img.external_id)

        cache_images_task.delay(cache_image_list, height, width)

        return Response(serializer.data)

    # for create when needed
    def perform_create(self, serializer):
        self.service.create(serializer.validated_data)