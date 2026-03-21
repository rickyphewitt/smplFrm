import logging
from typing import Any, Dict, Tuple

from django.db.models import QuerySet

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
        """Not supported for Config."""
        raise NotImplementedError("Config listing not supported")

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
            config = Config.objects.create(name="smplFrm Default", is_active=True)
            created = True
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
