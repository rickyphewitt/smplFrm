from django.db import models

from smplfrm.models.base import ModelBase


class Plugin(ModelBase):
    """Plugin configuration stored in the database."""

    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=200, default="", blank=True)
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "plugin"
