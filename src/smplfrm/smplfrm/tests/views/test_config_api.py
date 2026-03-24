from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from smplfrm.models import Config


class TestConfigAPI(TestCase):
    """Test suite for Config API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        Config.objects.all().delete()
        self.config = Config.objects.create(
            name="smplFrm Default",
            is_active=True,
            display_date=True,
            display_clock=True,
            image_refresh_interval=30000,
            image_transition_type="fade",
        )
        self.url = f"/api/v1/configs/{self.config.external_id}"

    def test_get_config(self):
        """Test retrieving a config via API."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.config.external_id)
        self.assertEqual(response.data["name"], "smplFrm Default")
        self.assertTrue(response.data["is_active"])
        self.assertTrue(response.data["display_date"])
        self.assertTrue(response.data["display_clock"])
        self.assertEqual(response.data["image_refresh_interval"], 30000)
        self.assertEqual(response.data["image_transition_type"], "fade")

    def test_update_config_with_put(self):
        """Test updating a config via API with PUT."""
        update_data = {
            "name": "smplFrm Default",
            "display_date": False,
            "display_clock": False,
            "image_refresh_interval": 60000,
            "image_transition_interval": 5000,
            "image_zoom_effect": False,
            "image_transition_type": "zoom",
            "image_cache_timeout": 600,
        }

        response = self.client.put(
            self.url, update_data, content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["display_date"])
        self.assertFalse(response.data["display_clock"])
        self.assertEqual(response.data["image_refresh_interval"], 60000)
        self.assertEqual(response.data["image_transition_interval"], 5000)
        self.assertFalse(response.data["image_zoom_effect"])
        self.assertEqual(response.data["image_transition_type"], "zoom")
        self.assertEqual(response.data["image_cache_timeout"], 600)

        self.config.refresh_from_db()
        self.assertFalse(self.config.display_date)
        self.assertEqual(self.config.image_refresh_interval, 60000)

    def test_patch_config_forbidden(self):
        """Test that PATCH is not allowed."""
        update_data = {
            "display_date": False,
        }

        response = self.client.patch(
            self.url, update_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_config_forbidden(self):
        """Test that creating config via API is forbidden."""
        response = self.client.post("/api/v1/configs", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_configs(self):
        """Test listing configs returns paginated results, system-managed first."""
        Config.objects.create(name="custom-20260101", is_active=False)
        Config.objects.create(name="smplFrm Minimal", is_active=False)

        response = self.client.get("/api/v1/configs")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [c["name"] for c in response.data["results"]]
        # system-managed should come first
        smpl_names = [n for n in names if n.startswith("smplFrm")]
        custom_names = [n for n in names if not n.startswith("smplFrm")]
        self.assertEqual(names, smpl_names + custom_names)

    def test_update_config_with_invalid_data(self):
        """Test that invalid data returns error."""
        update_data = {
            "name": "smplFrm Default",
            "display_date": False,
            "display_clock": False,
            "image_refresh_interval": -1,
            "image_transition_interval": 5000,
            "image_zoom_effect": False,
            "image_transition_type": "zoom",
            "image_cache_timeout": 300,
        }

        response = self.client.put(
            self.url, update_data, content_type="application/json"
        )

        self.assertNotEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_config_forbidden(self):
        """Test that deleting config via API is forbidden."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_apply_preset_creates_custom_copy(self):
        """Test applying a preset when active config is system-managed."""
        preset = Config.objects.create(
            name="smplFrm Minimal",
            is_active=False,
            display_date=False,
            display_clock=False,
        )

        response = self.client.post(f"/api/v1/configs/{preset.external_id}/apply")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["name"].startswith("custom-"))
        self.assertTrue(response.data["is_active"])
        self.assertFalse(response.data["display_date"])
        self.assertFalse(response.data["display_clock"])

        # Original preset should be untouched
        preset.refresh_from_db()
        self.assertFalse(preset.is_active)

        # Old active config should be deactivated
        self.config.refresh_from_db()
        self.assertFalse(self.config.is_active)

    def test_apply_preset_returns_400_when_active_is_custom(self):
        """Test that apply returns 400 when active config is already custom."""
        self.config.name = "custom-20260101"
        self.config.save()

        preset = Config.objects.create(
            name="smplFrm Minimal",
            is_active=False,
            display_date=False,
            display_clock=False,
        )

        response = self.client.post(f"/api/v1/configs/{preset.external_id}/apply")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_apply_preset_config_limit(self):
        """Test that applying returns 400 when config limit is exceeded."""
        from smplfrm.services.config_service import CONFIG_LIMIT

        # Create configs up to the limit (self.config is 1 already)
        for i in range(CONFIG_LIMIT - 1):
            Config.objects.create(name=f"config-{i}", is_active=False)

        preset = Config.objects.create(
            name="smplFrm Minimal",
            is_active=False,
        )
        # Now at CONFIG_LIMIT + 1 (including preset), but non-deleted count matters
        # self.config (active, system-managed) + CONFIG_LIMIT-1 + preset = CONFIG_LIMIT + 1
        response = self.client.post(f"/api/v1/configs/{preset.external_id}/apply")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
