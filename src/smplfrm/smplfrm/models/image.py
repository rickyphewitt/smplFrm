from django.db import models

from smplfrm.models.base import ModelBase


class Image(ModelBase):

    name = models.CharField(max_length=100)
    file_name = models.CharField(max_length=100)
    file_path = models.CharField(max_length=200)
    view_count = models.PositiveIntegerField(default=0)
