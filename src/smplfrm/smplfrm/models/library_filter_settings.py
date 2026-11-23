from django.db import models

from smplfrm.models.base import ModelBase


class LibraryFilterSettings(ModelBase):
    """Single-row switch for library filtering.

    The row is created by a data migration with ``enabled=False``.
    """

    enabled = models.BooleanField(default=False)

    class Meta:
        db_table = "library_filter_settings"
