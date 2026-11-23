from django.db import models

from smplfrm.models.base import ModelBase


class LibraryFilter(ModelBase):
    """A named set of rules over library images. At most one is active."""

    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True, default="")
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = "library_filter"
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=models.Q(is_active=True),
                name="unique_active_library_filter",
            ),
            # Only live filters reserve a name, so a deleted filter's name
            # can be used again.
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(deleted=False),
                name="uniq_library_filter_name",
            ),
        ]
