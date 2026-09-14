"""Tests for image list endpoint with sort parameter."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from smplfrm.models import Image


class TestImageSort(TestCase):
    """Test suite for image list sorting."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        now = timezone.now()

        # Create images with varying view counts
        self.img1 = Image.objects.create(
            name="img1", file_path="/test/", file_name="img1.jpg"
        )
        self.img1.view_count = 5
        Image.objects.filter(external_id=self.img1.external_id).update(
            view_count=5, created=now - timedelta(hours=3)
        )

        self.img2 = Image.objects.create(
            name="img2", file_path="/test/", file_name="img2.jpg"
        )
        Image.objects.filter(external_id=self.img2.external_id).update(
            view_count=2, created=now - timedelta(hours=1)
        )

        self.img3 = Image.objects.create(
            name="img3", file_path="/test/", file_name="img3.jpg"
        )
        Image.objects.filter(external_id=self.img3.external_id).update(
            view_count=2, created=now - timedelta(hours=2)
        )

    def test_sort_display_priority_accepted(self):
        """Test that sort=display_priority is accepted and orders correctly."""
        response = self.client.get(
            "/api/v1/images?sort=display_priority",
            HTTP_ACCEPT="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        ids = [item["id"] for item in data["data"]]

        # Expected order: img2 (view=2, newer), img3 (view=2, older), img1 (view=5)
        self.assertEqual(ids[0], self.img2.external_id)
        self.assertEqual(ids[1], self.img3.external_id)
        self.assertEqual(ids[2], self.img1.external_id)

    def test_sort_unknown_profile_rejected(self):
        """Test that unknown sort profile is rejected with 400."""
        response = self.client.get(
            "/api/v1/images?sort=unknown",
            HTTP_ACCEPT="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("errors", data)

    def test_sort_comma_separated_rejected(self):
        """Test that comma-separated sort is rejected."""
        response = self.client.get(
            "/api/v1/images?sort=display_priority,name",
            HTTP_ACCEPT="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, 400)

    def test_sort_direction_prefix_rejected(self):
        """Test that direction-prefixed sort is rejected."""
        response = self.client.get(
            "/api/v1/images?sort=-display_priority",
            HTTP_ACCEPT="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, 400)

    def test_pagination_preserves_sort(self):
        """Test that pagination links preserve sort parameter."""
        response = self.client.get(
            "/api/v1/images?sort=display_priority&page[number]=1",
            HTTP_ACCEPT="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check pagination links contain sort parameter
        if "links" in data and "next" in data["links"] and data["links"]["next"]:
            self.assertIn("sort=display_priority", data["links"]["next"])

    def test_empty_collection_returns_200(self):
        """Test that empty collection returns 200 with empty data array."""
        # Delete all images
        Image.objects.all().update(deleted=True)

        response = self.client.get(
            "/api/v1/images?sort=display_priority",
            HTTP_ACCEPT="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["data"], [])

    def test_default_sort_when_omitted(self):
        """Test that omitting sort uses default -created order."""
        response = self.client.get(
            "/api/v1/images",
            HTTP_ACCEPT="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        ids = [item["id"] for item in data["data"]]

        # Default order should be newest first (-created)
        # img2 is newest, img3 next, img1 oldest
        self.assertEqual(ids[0], self.img2.external_id)

    def test_next_image_removed(self):
        """Test that /images/next endpoint is no longer available."""
        response = self.client.get(
            "/api/v1/images/next",
            HTTP_ACCEPT="application/vnd.api+json",
        )

        # Should return 403 (resource enumeration protection), 404, or 405
        self.assertIn(response.status_code, [403, 404, 405])
