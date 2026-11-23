from django.db import models

from smplfrm.models.base import ModelBase

# Must equal MAX_TAG_LENGTH in services/library/canonicalize.py. Kept as a
# literal so models do not import from the service layer.
TAG_VALUE_MAX_LENGTH = 200


class Tag(ModelBase):
    """A keyword found in image metadata, deduplicated on its canonical form."""

    # Canonical form (see services/library/canonicalize.py)
    value = models.CharField(max_length=TAG_VALUE_MAX_LENGTH, unique=True)
    # First-seen form with the author's casing, for display
    display_value = models.CharField(max_length=TAG_VALUE_MAX_LENGTH, default="")

    class Meta:
        db_table = "tag"
