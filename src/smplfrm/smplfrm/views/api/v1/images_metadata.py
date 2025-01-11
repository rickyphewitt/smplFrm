import logging

from django.core.exceptions import PermissionDenied
from rest_framework import viewsets
from smplfrm.models import ImageMetadata
from smplfrm.services.image_metadata_service import ImageMetadataService
from smplfrm.views.serializers.v1.image_metadata_serializer import ImageMetadataSerializer

logger = logging.getLogger(__name__)


class ImagesMetadata(viewsets.ModelViewSet):

    queryset = ImageMetadata.objects.all()
    serializer_class = ImageMetadataSerializer
    lookup_field = "external_id"


    def get_queryset(self):
        """
        @ToDo when more robust filtering is needed
        look into django-filter package
        """
        queryset = ImageMetadata.objects.all()
        image_external_id = self.request.query_params.get('image__external_id')
        if image_external_id is not None:
            queryset = queryset.filter(image__external_id=image_external_id)
        return queryset

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ImageMetadataService()

    # for now only allow list and read
    def create(self, request, *args, **kwargs):
        raise PermissionDenied()

    def update(self, request, *args, **kwargs):
        raise PermissionDenied()

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied()
