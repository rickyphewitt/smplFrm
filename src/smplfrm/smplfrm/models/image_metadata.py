from django.db import models

from smplfrm.models.base import ModelBase
from smplfrm.models.image import Image


class ImageMetadata(ModelBase):
    image = models.OneToOneField(Image, on_delete=models.CASCADE, related_name="meta")
    exif = models.JSONField()
    taken = models.DateTimeField(null=True)
