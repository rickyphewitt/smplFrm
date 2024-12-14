import logging

from rest_framework.views import APIView
from rest_framework import mixins
from rest_framework import generics
from django.core.exceptions import PermissionDenied
from rest_framework.decorators import action
from django.http import HttpResponse


from smplfrm.models import Image
from smplfrm.views.serializers.v1.image_serializer import ImageSerializer

from rest_framework import viewsets

from smplfrm.services.image_service import ImageService
from smplfrm.services.image_manipulation_service import ImageManipulationService

from smplfrm.settings import BASE_DIR
logger = logging.getLogger(__name__)

class Images(viewsets.ModelViewSet):

    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    lookup_field = "external_id"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ImageService()
        self.image_manipulation = ImageManipulationService()

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
        displayed_image = self.image_manipulation.display(image, 0, 0)
        response = HttpResponse(status=200, headers={'Content-type': 'image/jpeg'})
        response.write(displayed_image.tobytes())
        return response

    @action(methods=['get'], detail=False, url_path="next")
    def next_image(self, request):
        """

        :param request:
        :return:
        """

        image = self.service.get_next()
        logger.info(f"BASE DIR: {BASE_DIR}")
        if image:
            # get w/h of caller
            width = request.GET.get('width', '100')
            height = request.GET.get('height', '100')

            displayed_image = self.image_manipulation.display(image, int(height), int(width))
            response = HttpResponse(status=200, headers={'Content-type': 'image/jpeg'})
            response.write(displayed_image.tobytes())
            return response
        else:
            return HttpResponse(status=404)

    # for create when needed
    def perform_create(self, serializer):
        self.service.create(serializer.validated_data)
