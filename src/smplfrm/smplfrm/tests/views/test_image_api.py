from django.test import TestCase
from rest_framework.test import APIClient

from smplfrm.models import Image


class TestImageAPI(TestCase):
    """Test suite for Image API serialization."""

    def setUp(self):
        self.client = APIClient()
        self.image = Image.objects.create(
            name="test", file_path="/tmp/", file_name="test.jpg"
        )

    def test_get_image_includes_view_count(self):
        """Test that image API response includes view_count field."""
        response = self.client.get(f"/api/v1/images/{self.image.external_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("view_count", response.data)
        self.assertEqual(response.data["view_count"], 0)
