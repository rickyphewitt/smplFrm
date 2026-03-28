from django.db import models

from smplfrm.models.base import ModelBase


class Config(ModelBase):
    """User configuration settings for smplFrm."""

    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=200, default="", blank=True)
    is_active = models.BooleanField(default=False)

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

    # Image Processing
    image_fill_mode = models.CharField(
        max_length=20,
        default="blur",
        choices=[
            ("blur", "Blur"),
            ("border", "Border"),
            ("zoom_to_fill", "Zoom to Fill"),
        ],
    )
    force_date_from_path = models.BooleanField(default=True)

    # General
    timezone = models.CharField(max_length=50, default="America/Los_Angeles")
    plugins = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "config"
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=models.Q(is_active=True),
                name="unique_active_config",
            ),
        ]
