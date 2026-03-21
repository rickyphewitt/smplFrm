from django.db import IntegrityError
from django.test import TestCase

from smplfrm.models import Config


class TestConfig(TestCase):
    """Test suite for Config model."""

    def test_create_config_with_defaults(self):
        """Test creating a config with default values."""
        config = Config.objects.create(name="test config")

        # New fields
        self.assertEqual(config.name, "test config")
        self.assertFalse(config.is_active)

        # Display Elements
        self.assertTrue(config.display_date)
        self.assertTrue(config.display_clock)

        # Image Display & Timing
        self.assertEqual(config.image_refresh_interval, 30000)
        self.assertEqual(config.image_transition_interval, 10000)
        self.assertTrue(config.image_zoom_effect)
        self.assertEqual(config.image_transition_type, "random")

        # Cache
        self.assertEqual(config.image_cache_timeout, 300)

    def test_update_config(self):
        """Test updating config values."""
        config = Config.objects.create(name="test config")

        config.display_date = False
        config.image_refresh_interval = 45000
        config.save()

        config.refresh_from_db()
        self.assertFalse(config.display_date)
        self.assertEqual(config.image_refresh_interval, 45000)

    def test_transition_type_choices(self):
        """Test valid transition type choices."""
        config = Config.objects.create(name="test config")
        valid_types = ["random", "fade", "slide-left", "slide-right", "zoom", "none"]

        for transition_type in valid_types:
            config.image_transition_type = transition_type
            config.save()
            config.refresh_from_db()
            self.assertEqual(config.image_transition_type, transition_type)

    def test_name_is_unique(self):
        """Test that config name must be unique."""
        Config.objects.create(name="duplicate")
        with self.assertRaises(IntegrityError):
            Config.objects.create(name="duplicate")

    def test_only_one_active_config_allowed(self):
        """Test that only one config can be active at a time."""
        Config.objects.create(name="active", is_active=True)
        with self.assertRaises(IntegrityError):
            Config.objects.create(name="also active", is_active=True)

    def test_multiple_inactive_configs_allowed(self):
        """Test that multiple inactive configs are allowed."""
        Config.objects.create(name="inactive 1", is_active=False)
        Config.objects.create(name="inactive 2", is_active=False)
        self.assertEqual(Config.objects.filter(is_active=False).count(), 2)
