import random
import string

from django.db import models


def generate_external_id():
    return "".join(
        random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
        for _ in range(16)
    )


class ModelBase(models.Model):

    # the id to serialize out for apis
    external_id = models.CharField(max_length=16, default=generate_external_id)

    created = models.DateTimeField(auto_now_add=True)
    # quality of life
    updated = models.DateTimeField(auto_now=True)

    # soft delete support
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True
        app_label = "smplfrm"
