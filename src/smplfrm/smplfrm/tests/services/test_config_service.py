from django.test import TestCase
from unittest.mock import patch

from smplfrm.models import Config
from smplfrm.services.config_service import ConfigService, PRESET_PREFIX, CONFIG_LIMIT


class TestConfigService(TestCase):
    """Test suite for ConfigService."""

    def setUp(self):
        """Set up test fixtures."""
        Config.objects.all().delete()
        self.config = Config.objects.create(
            name="smplFrm Default",
            is_active=True,
            display_date=True,
            display_clock=True,
            image_refresh_interval=30000,
        )

    def test_get_active_returns_active_config(self):
        """Test get_active returns the active config."""
        service = ConfigService()
        active, created = service.get_active()

        self.assertEqual(active.external_id, self.config.external_id)
        self.assertTrue(active.is_active)
        self.assertFalse(created)

    def test_get_active_ignores_inactive(self):
        """Test get_active ignores inactive configs."""
        self.config.is_active = False
        self.config.name = "inactive config"
        self.config.save()

        service = ConfigService()
        active, created = service.get_active()

        self.assertNotEqual(active.external_id, self.config.external_id)
        self.assertTrue(active.is_active)
        self.assertEqual(active.name, "smplFrm Default")
        self.assertTrue(created)

    def test_get_active_creates_if_none_exist(self):
        """Test get_active creates a config if none exist."""
        Config.objects.all().delete()

        service = ConfigService()
        active, created = service.get_active()

        self.assertIsNotNone(active)
        self.assertTrue(active.is_active)
        self.assertEqual(active.name, "smplFrm Default")
        self.assertEqual(Config.objects.count(), 1)
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

        self.assertFalse(config.display_date)
        self.assertFalse(config.display_clock)
        self.assertEqual(config.image_refresh_interval, 60000)
        self.assertEqual(config.image_transition_type, "fade")

    def test_load_config_preserves_existing_config(self):
        """Test that existing config is not overridden by environment variables."""
        self.config.display_date = False
        self.config.image_refresh_interval = 45000
        self.config.save()

        service = ConfigService()
        config = service.load_config()

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

        retrieved = Config.objects.get(external_id=self.config.external_id)
        self.assertFalse(retrieved.display_date)
        self.assertEqual(retrieved.image_refresh_interval, 60000)


class TestSyncPresets(TestCase):
    """Test suite for ConfigService.sync_presets()."""

    def setUp(self):
        self.service = ConfigService()

    def test_sync_presets_creates_all_presets(self):
        """Test that sync_presets creates all preset configs."""
        self.service.sync_presets()

        expected = [
            "smplFrm Default",
            "smplFrm Info",
            "smplFrm Media",
            "smplFrm Minimal",
        ]
        names = list(
            Config.objects.filter(name__startswith=PRESET_PREFIX)
            .order_by("name")
            .values_list("name", flat=True)
        )
        self.assertEqual(names, expected)

    def test_sync_presets_sets_correct_values(self):
        """Test that preset field values match JSON definitions."""
        self.service.sync_presets()

        minimal = Config.objects.get(name="smplFrm Minimal")
        self.assertFalse(minimal.display_date)
        self.assertFalse(minimal.display_clock)
        self.assertFalse(minimal.is_active)

        info = Config.objects.get(name="smplFrm Info")
        self.assertTrue(info.display_date)
        self.assertTrue(info.display_clock)
        self.assertFalse(info.is_active)

    def test_sync_presets_idempotent(self):
        """Test that running sync_presets twice does not create duplicates."""
        self.service.sync_presets()
        count_after_first = Config.objects.filter(
            name__startswith=PRESET_PREFIX
        ).count()

        self.service.sync_presets()
        count_after_second = Config.objects.filter(
            name__startswith=PRESET_PREFIX
        ).count()

        self.assertEqual(count_after_first, count_after_second)

    def test_sync_presets_updates_changed_values(self):
        """Test that sync_presets updates a preset when its DB value differs from JSON."""
        self.service.sync_presets()

        # Simulate a manual DB change that diverges from the JSON
        minimal = Config.objects.get(name="smplFrm Minimal")
        minimal.display_date = True
        minimal.save()

        # Re-sync should restore the JSON value
        self.service.sync_presets()

        minimal.refresh_from_db()
        self.assertFalse(minimal.display_date)


class TestConfigList(TestCase):
    """Test suite for ConfigService.list()."""

    def test_list_returns_system_managed_first(self):
        """Test that list returns system-managed configs before custom ones."""
        Config.objects.all().delete()
        Config.objects.create(name="custom-20260101", is_active=False)
        Config.objects.create(name="smplFrm Default", is_active=True)
        Config.objects.create(name="smplFrm Minimal", is_active=False)

        service = ConfigService()
        configs = list(service.list())
        names = [c.name for c in configs]

        self.assertEqual(names[0], "smplFrm Default")
        self.assertEqual(names[1], "smplFrm Minimal")
        self.assertEqual(names[2], "custom-20260101")

    def test_list_excludes_deleted(self):
        """Test that list excludes soft-deleted configs."""
        Config.objects.all().delete()
        Config.objects.create(name="active", is_active=True)
        Config.objects.create(name="deleted", is_active=False, deleted=True)

        service = ConfigService()
        self.assertEqual(service.list().count(), 1)


class TestApplyPreset(TestCase):
    """Test suite for ConfigService.apply_preset()."""

    def setUp(self):
        Config.objects.all().delete()
        self.service = ConfigService()
        self.active = Config.objects.create(
            name="smplFrm Default",
            is_active=True,
            display_date=True,
            display_clock=True,
        )
        self.preset = Config.objects.create(
            name="smplFrm Minimal",
            is_active=False,
            display_date=False,
            display_clock=False,
        )

    def test_apply_creates_copy_when_active_is_system_managed(self):
        """Test that applying creates a custom copy when active is system-managed."""
        result = self.service.apply_preset(self.preset.external_id)

        self.assertTrue(result.name.startswith("custom-"))
        self.assertTrue(result.is_active)
        self.assertFalse(result.display_date)
        self.assertFalse(result.display_clock)

        self.active.refresh_from_db()
        self.assertFalse(self.active.is_active)

    def test_apply_raises_when_active_is_custom(self):
        """Test that apply raises ValueError when active config is custom."""
        self.active.name = "custom-existing"
        self.active.save()

        with self.assertRaises(ValueError):
            self.service.apply_preset(self.preset.external_id)

    def test_apply_raises_when_limit_exceeded(self):
        """Test that apply raises ValueError when config limit is reached."""
        for i in range(CONFIG_LIMIT - 2):  # -2 for active + preset already created
            Config.objects.create(name=f"filler-{i}", is_active=False)

        with self.assertRaises(ValueError):
            self.service.apply_preset(self.preset.external_id)
