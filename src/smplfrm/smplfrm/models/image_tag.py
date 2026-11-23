from django.db import models

from smplfrm.models.base import ModelBase


class ImageTag(ModelBase):
    """Links an image to a tag found in its embedded metadata."""

    image = models.ForeignKey(
        "smplfrm.Image", on_delete=models.CASCADE, related_name="image_tags"
    )
    tag = models.ForeignKey(
        "smplfrm.Tag", on_delete=models.CASCADE, related_name="image_tags"
    )
    # Subset of ["exif", "iptc", "xmp"], sorted
    sources = models.JSONField(default=list)
    # Hierarchical paths that end in this tag; '|' separates segments,
    # e.g. ["People|Family|Alice"]
    raw_hierarchy = models.JSONField(default=list)

    class Meta:
        db_table = "image_tag"
        constraints = [
            models.UniqueConstraint(fields=["image", "tag"], name="uniq_image_tag"),
        ]
        indexes = [models.Index(fields=["tag"])]
