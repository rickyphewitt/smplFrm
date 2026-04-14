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


from smplfrm.services import ImageService, LibraryService


class TestImageDimensionBoundsExploration(TestCase):
    """Test suite for invalid dimension parameter handling."""

    def setUp(self):
        self.client = APIClient()
        self.image = Image.objects.create(
            name="test", file_path="/tmp/", file_name="test.jpg"
        )

    def test_display_image_non_numeric_width_returns_400(self):
        """Test that non-numeric width returns 400."""
        response = self.client.get(
            f"/api/v1/images/{self.image.external_id}/display?width=abc&height=100"
        )
        self.assertEqual(response.status_code, 400)

    def test_display_image_zero_width_returns_400(self):
        """Test that zero width returns 400."""
        response = self.client.get(
            f"/api/v1/images/{self.image.external_id}/display?width=0&height=100"
        )
        self.assertEqual(response.status_code, 400)

    def test_display_image_negative_width_returns_400(self):
        """Test that negative width returns 400."""
        response = self.client.get(
            f"/api/v1/images/{self.image.external_id}/display?width=-50&height=100"
        )
        self.assertEqual(response.status_code, 400)

    def test_display_image_exceeds_max_dimension_returns_400(self):
        """Test that dimensions exceeding MAX_IMAGE_DIMENSION return 400."""
        response = self.client.get(
            f"/api/v1/images/{self.image.external_id}/display?width=99999&height=99999"
        )
        self.assertEqual(response.status_code, 400)

    def test_next_image_non_numeric_width_returns_400(self):
        """Test that non-numeric width on next_image returns 400."""
        response = self.client.get("/api/v1/images/next?width=abc&height=100")
        self.assertEqual(response.status_code, 400)


class TestImageDimensionBoundsPreservation(TestCase):
    """Test suite for valid dimension parameter handling."""

    def setUp(self):
        self.client = APIClient()
        self.image_service = ImageService()
        LibraryService().scan()
        self.image = self.image_service.list()[0]
        self.uri = "/api/v1/images"

    def test_display_image_with_valid_dimensions_returns_200(self):
        """Test that valid dimensions return 200 with image data."""
        response = self.client.get(
            f"{self.uri}/{self.image.external_id}/display?width=800&height=600"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-type"], "image/jpeg")
        self.assertGreater(len(response.content), 0)

    def test_display_image_default_dimensions_returns_200(self):
        """Test that omitted dimensions default to 100x100 and return 200."""
        response = self.client.get(f"{self.uri}/{self.image.external_id}/display")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-type"], "image/jpeg")
        self.assertGreater(len(response.content), 0)

    def test_display_image_file_not_found_returns_404(self):
        """Test that a missing file on disk returns 404."""
        missing_image = Image.objects.create(
            name="missing", file_path="/does/not/exist/", file_name="gone.jpg"
        )
        response = self.client.get(
            f"{self.uri}/{missing_image.external_id}/display?width=100&height=100"
        )
        self.assertEqual(response.status_code, 404)

    def test_next_image_with_valid_dimensions_returns_200(self):
        """Test that next_image with valid dimensions returns 200."""
        response = self.client.get(f"{self.uri}/next?width=800&height=600")
        self.assertEqual(response.status_code, 200)

    def test_next_image_default_dimensions_returns_200(self):
        """Test that next_image with omitted dimensions returns 200."""
        response = self.client.get(f"{self.uri}/next")
        self.assertEqual(response.status_code, 200)
