from django.db import models

from smplfrm.models.base import ModelBase


class Config(ModelBase):
    """User configuration settings for smplFrm."""

    # Display Elements
    display_date = models.BooleanField(default=True)
    display_clock = models.BooleanField(default=True)

    # Image Display & Timing
    image_refresh_interval = models.PositiveIntegerField(default=30000)
    image_transition_interval = models.PositiveIntegerField(default=10000)
    image_zoom_effect = models.BooleanField(default=True)
    image_transition_type = models.CharField(
        max_length=20,
        default="random",
        choices=[
            ("random", "Random"),
            ("fade", "Fade"),
            ("slide-left", "Slide Left"),
            ("slide-right", "Slide Right"),
            ("zoom", "Zoom"),
            ("none", "None"),
        ],
    )

    # Cache
    image_cache_timeout = models.PositiveIntegerField(default=300)

    class Meta:
        db_table = "config"
