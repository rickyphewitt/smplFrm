import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

from django.db.models import Case, When, Value, IntegerField, QuerySet

from smplfrm.models import Config
from smplfrm.settings import (
    SMPL_FRM_DISPLAY_CLOCK,
    SMPL_FRM_DISPLAY_DATE,
    SMPL_FRM_IMAGE_CACHE_TIMEOUT,
    SMPL_FRM_IMAGE_REFRESH_INTERVAL,
    SMPL_FRM_IMAGE_TRANSITION_INTERVAL,
    SMPL_FRM_IMAGE_TRANSITION_TYPE,
    SMPL_FRM_IMAGE_ZOOM_EFFECT,
)

from .base_service import BaseService

logger = logging.getLogger(__name__)

PRESETS_DIR = Path(__file__).resolve().parent.parent / "presets"
PRESET_PREFIX = "smplFrm "
CONFIG_LIMIT = 10

# Fields to copy when applying a preset
_PRESET_FIELDS = [
    "display_date",
    "display_clock",
    "image_refresh_interval",
    "image_transition_interval",
    "image_zoom_effect",
    "image_transition_type",
    "image_cache_timeout",
]


class ConfigService(BaseService):
    """Service for managing SmplFrm Settings."""

    def create(self, data: Dict[str, Any]) -> Config:
        """Not supported for Config."""
        raise NotImplementedError("Config creation not supported")

    def read(self, ext_id: str, deleted: bool = False) -> Config:
        """Retrieve settings by external ID.

        Args:
            ext_id: External identifier
            deleted: Whether to include soft-deleted records

        Returns:
            Config instance
        """
        return Config.objects.get(external_id=ext_id, deleted=deleted)

    def list(self, **kwargs) -> QuerySet:
        """Return all non-deleted configs: active first, then managed, then custom."""
        return (
            Config.objects.filter(deleted=False)
            .annotate(
                sort_order=Case(
                    When(name__startswith=PRESET_PREFIX, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )
            .order_by("-is_active", "sort_order", "name")
        )

    def update(self, config: Config) -> Config:
        """Update an existing Config record.

        Args:
            config: Config instance to update

        Returns:
            Updated Config instance
        """
        logger.info(
            f"Updating config {config.external_id}: display_date={config.display_date}, display_clock={config.display_clock}, refresh={config.image_refresh_interval}"
        )
        config.save()
        return config

    def delete(self, ext_id: str) -> None:
        """Not supported for Config."""
        raise NotImplementedError("Config deletion not supported")

    def destroy(self, ext_id: str) -> None:
        """Not supported for Config."""
        raise NotImplementedError("Config destruction not supported")

    def get_active(self) -> Tuple[Config, bool]:
        """Get or create the active config instance.

        Returns:
            Tuple of (Config instance, created flag)
        """
        config = Config.objects.filter(is_active=True).first()
        created = False
        if not config:
            config, created = Config.objects.get_or_create(
                name="smplFrm Default", defaults={"is_active": True}
            )
            if not created:
                config.is_active = True
                config.save()
        logger.debug(f"Active config: {config.external_id}")
        return config, created

    def load_config(self) -> Config:
        """Load configuration from the database.

        On first creation, initializes config with environment variable values.
        Existing configs are returned as-is without modification.

        Returns:
            Config instance
        """
        config, created = self.get_active()
        if created:
            logger.info("Created new config from environment variables")
            config.display_date = SMPL_FRM_DISPLAY_DATE
            config.display_clock = SMPL_FRM_DISPLAY_CLOCK
            config.image_refresh_interval = SMPL_FRM_IMAGE_REFRESH_INTERVAL
            config.image_transition_interval = SMPL_FRM_IMAGE_TRANSITION_INTERVAL
            config.image_zoom_effect = SMPL_FRM_IMAGE_ZOOM_EFFECT
            config.image_transition_type = SMPL_FRM_IMAGE_TRANSITION_TYPE
            config.image_cache_timeout = SMPL_FRM_IMAGE_CACHE_TIMEOUT
            config = self.update(config)

        return config

    def sync_presets(self) -> None:
        """Sync preset JSON files to the database.

        Reads all JSON files from the presets directory, creates or updates
        Config rows with the smplFrm prefix. Idempotent — safe to call on
        every startup.
        """
        for path in sorted(PRESETS_DIR.glob("*.json")):
            data = json.loads(path.read_text())
            name = f"{PRESET_PREFIX}{data.pop('name')}"
            config, created = Config.objects.get_or_create(
                name=name, defaults={**data, "is_active": False}
            )
            if not created:
                updated = False
                for field, value in data.items():
                    if getattr(config, field) != value:
                        setattr(config, field, value)
                        updated = True
                if updated:
                    config.save()
                    logger.info(f"Updated preset: {name}")
            else:
                logger.info(f"Created preset: {name}")

    def apply_preset(self) -> Config:
        """Create a custom copy of the current active config.

        Called by the save flow when the active config is system-managed.
        Creates a new custom config with the same field values and activates it.

        Returns:
            The new custom Config instance

        Raises:
            ValueError: If active config is already custom or limit exceeded
        """
        active, _ = self.get_active()

        if not active.name.startswith(PRESET_PREFIX):
            raise ValueError("Active config is already custom. Use PUT to update it.")

        if Config.objects.filter(deleted=False).count() >= CONFIG_LIMIT:
            raise ValueError(
                f"Config limit of {CONFIG_LIMIT} reached. "
                "Delete an existing config or select a custom one."
            )

        active.is_active = False
        active.save()

        name = f"custom-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        new_config = Config(name=name, is_active=True)
        for field in _PRESET_FIELDS:
            setattr(new_config, field, getattr(active, field))
        new_config.save()
        return new_config

    def activate(self, ext_id: str) -> Config:
        """Activate a config by external ID.

        Deactivates the current active config and activates the target.

        Args:
            ext_id: External ID of the config to activate

        Returns:
            The newly activated Config instance
        """
        active = Config.objects.filter(is_active=True).first()
        if active:
            active.is_active = False
            active.save()

        target = self.read(ext_id)
        target.is_active = True
        target.save()
        return target
