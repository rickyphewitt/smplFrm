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
        self.assertTrue(response.data["display_date"])
        self.assertTrue(response.data["display_clock"])
        self.assertEqual(response.data["image_refresh_interval"], 30000)
        self.assertEqual(response.data["image_transition_type"], "fade")

    def test_update_config(self):
        """Test updating a config via API."""
        update_data = {
            "display_date": False,
            "image_refresh_interval": 60000,
            "image_transition_type": "zoom",
        }

        response = self.client.patch(self.url, update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["display_date"])
        self.assertEqual(response.data["image_refresh_interval"], 60000)
        self.assertEqual(response.data["image_transition_type"], "zoom")

        # Verify persistence
        self.config.refresh_from_db()
        self.assertFalse(self.config.display_date)
        self.assertEqual(self.config.image_refresh_interval, 60000)

    def test_create_config_forbidden(self):
        """Test that creating config via API is forbidden."""
        response = self.client.post("/api/v1/configs", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_config_forbidden(self):
        """Test that listing configs via API is forbidden."""
        response = self.client.get("/api/v1/configs")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_config_forbidden(self):
        """Test that deleting config via API is forbidden."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
