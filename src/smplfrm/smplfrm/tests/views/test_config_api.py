from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from smplfrm.models import Config


class TestConfigAPI(TestCase):
    """Test suite for Config API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
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

    def test_list_config_forbidden(self):
        """Test that listing configs via API is forbidden."""
        response = self.client.get("/api/v1/configs")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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
