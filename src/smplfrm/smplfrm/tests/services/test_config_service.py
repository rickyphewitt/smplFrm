from django.test import TestCase
from unittest.mock import patch

from smplfrm.models import Config
from smplfrm.services.config_service import ConfigService


class TestConfigService(TestCase):
    """Test suite for ConfigService."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = Config.objects.create(
            display_date=True,
            display_clock=True,
            image_refresh_interval=30000,
        )

    def test_get_active_returns_first_config(self):
        """Test get_active returns the first non-deleted config."""
        service = ConfigService()
        active, created = service.get_active()

        self.assertEqual(active.external_id, self.config.external_id)
        self.assertTrue(active.display_date)
        self.assertFalse(created)

    def test_get_active_creates_if_none_exist(self):
        """Test get_active creates a config if none exist."""
        Config.objects.all().delete()

        service = ConfigService()
        active, created = service.get_active()

        self.assertIsNotNone(active)
        self.assertEqual(Config.objects.count(), 1)
        self.assertTrue(created)

    def test_get_active_ignores_deleted(self):
        """Test get_active ignores soft-deleted configs."""
        self.config.deleted = True
        self.config.save()

        service = ConfigService()
        active, created = service.get_active()

        # Should create a new one since existing is deleted
        self.assertNotEqual(active.external_id, self.config.external_id)
        self.assertFalse(active.deleted)
        self.assertTrue(created)

    @patch("smplfrm.services.config_service.SMPL_FRM_DISPLAY_DATE", False)
    @patch("smplfrm.services.config_service.SMPL_FRM_DISPLAY_CLOCK", False)
    @patch("smplfrm.services.config_service.SMPL_FRM_IMAGE_REFRESH_INTERVAL", 60000)
    @patch("smplfrm.services.config_service.SMPL_FRM_IMAGE_TRANSITION_TYPE", "fade")
    def test_load_config_uses_env_vars_on_first_creation(self):
        """Test that environment variables override defaults on first creation."""
        Config.objects.all().delete()

        service = ConfigService()
        config = service.load_config()

        # Should use environment variable values, not defaults
        self.assertFalse(config.display_date)
        self.assertFalse(config.display_clock)
        self.assertEqual(config.image_refresh_interval, 60000)
        self.assertEqual(config.image_transition_type, "fade")

    def test_load_config_preserves_existing_config(self):
        """Test that existing config is not overridden by environment variables."""
        # Set config to non-default values
        self.config.display_date = False
        self.config.image_refresh_interval = 45000
        self.config.save()

        service = ConfigService()
        config = service.load_config()

        # Should preserve existing values
        self.assertFalse(config.display_date)
        self.assertEqual(config.image_refresh_interval, 45000)

    def test_read_config(self):
        """Test reading a config by external ID."""
        service = ConfigService()
        retrieved = service.read(ext_id=self.config.external_id)
        self.assertEqual(retrieved.external_id, self.config.external_id)
        self.assertTrue(retrieved.display_date)
        self.assertEqual(retrieved.image_refresh_interval, 30000)

    def test_update_config(self):
        """Test updating a config."""
        service = ConfigService()
        self.config.display_date = False
        self.config.image_refresh_interval = 60000

        updated = service.update(self.config)

        self.assertFalse(updated.display_date)
        self.assertEqual(updated.image_refresh_interval, 60000)

        # Verify persistence
        retrieved = Config.objects.get(external_id=self.config.external_id)
        self.assertFalse(retrieved.display_date)
        self.assertEqual(retrieved.image_refresh_interval, 60000)
