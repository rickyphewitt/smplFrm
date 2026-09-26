import json

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from smplfrm.services import ImageService, LibraryService


class TestImagesView(TestCase):
    """Test suite for Images ViewSet with JSON:API format."""

    def setUp(self):
        self.client = APIClient()
        self.uri = "/api/v1/images"
        self.image_service = ImageService()
        self.full_image_data = {
            "name": "foo",
            "file_path": "./nested/file/",
            "file_name": "image.jpg",
        }

    def test_list_empty(self):
        """Test that list returns empty JSON:API collection."""
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertIn("data", body)
        self.assertEqual(len(body["data"]), 0)

    def test_list_with_images(self):
        """Test that list returns JSON:API collection with images."""
        created_image = self.image_service.create(self.full_image_data)

        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertIn("data", body)
        self.assertEqual(len(body["data"]), 1)
        self.assertEqual(body["data"][0]["type"], "images")
        self.assertEqual(body["data"][0]["id"], created_image.external_id)

    def test_list_pagination(self):
        """Test that list includes JSON:API pagination links and meta."""
        self.image_service.create(self.full_image_data)

        response = self.client.get(self.uri)
        body = response.json()
        self.assertIn("links", body)
        self.assertIn("meta", body)
        self.assertIn("pagination", body["meta"])

    def test_retrieve_image(self):
        """Test that retrieve returns JSON:API resource."""
        created_image = self.image_service.create(self.full_image_data)

        response = self.client.get(f"{self.uri}/{created_image.external_id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertIn("data", body)
        self.assertEqual(body["data"]["type"], "images")
        self.assertEqual(body["data"]["id"], created_image.external_id)
        self.assertIn("attributes", body["data"])
        self.assertEqual(body["data"]["attributes"]["name"], "foo")

    def test_retrieve_nonexistent_returns_403(self):
        """Test that retrieve of nonexistent image returns 403 (not 404)."""
        response = self.client.get(f"{self.uri}/nonexistent123456")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_not_allowed(self):
        """Test that POST returns 405."""
        response = self.client.post(
            self.uri,
            data=json.dumps({"data": {"type": "images", "attributes": {}}}),
            content_type="application/vnd.api+json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_not_allowed(self):
        """Test that PUT returns 405."""
        created_image = self.image_service.create(self.full_image_data)
        response = self.client.put(
            f"{self.uri}/{created_image.external_id}",
            data=json.dumps(
                {"data": {"type": "images", "id": created_image.external_id}}
            ),
            content_type="application/vnd.api+json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_not_allowed(self):
        """Test that PATCH returns 405."""
        created_image = self.image_service.create(self.full_image_data)
        response = self.client.patch(
            f"{self.uri}/{created_image.external_id}",
            data=json.dumps(
                {"data": {"type": "images", "id": created_image.external_id}}
            ),
            content_type="application/vnd.api+json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_not_allowed(self):
        """Test that DELETE returns 405."""
        created_image = self.image_service.create(self.full_image_data)
        response = self.client.delete(f"{self.uri}/{created_image.external_id}")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_display_image(self):
        """Test that display returns binary image (exempt from JSON:API)."""
        LibraryService().scan()
        image = self.image_service.list()[0]

        response = self.client.get(f"{self.uri}/{image.external_id}/display")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-type"], "image/jpeg")

        # Verify view count was updated
        displayed_image = self.image_service.read(image.external_id)
        self.assertEqual(image.view_count + 1, displayed_image.view_count)

    def test_display_cached_image(self):
        """Test that cached images are served correctly."""
        LibraryService().scan()
        image = self.image_service.list()[0]

        # First request caches the image
        response = self.client.get(f"{self.uri}/{image.external_id}/display")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Update image to point to nonexistent file
        image.file_path = "/does/Not/Exist.jpg"
        self.image_service.update(image)

        # Still served from cache
        response = self.client.get(f"{self.uri}/{image.external_id}/display")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_display_image_missing_file_returns_403(self):
        """Test that display returns an empty-body 403 for a file missing on disk."""
        LibraryService().scan()
        image = self.image_service.list()[0]
        image.file_path = "/does/Not/Exist.jpg"
        self.image_service.update(image)

        response = self.client.get(
            f"{self.uri}/{image.external_id}/display?filter[width]=1&filter[height]=2"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.content, b"")

    def test_display_image_unknown_id_returns_403(self):
        """Test that display returns an empty-body 403 for an unknown external_id."""
        response = self.client.get(
            f"{self.uri}/nonexistent123456/display?filter[width]=100&filter[height]=100"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.content, b"")

    def test_display_image_not_found_responses_are_indistinguishable(self):
        """Unknown-id and missing-file 403s must be byte-identical in status and body."""
        LibraryService().scan()
        image = self.image_service.list()[0]
        image.file_path = "/does/Not/Exist.jpg"
        self.image_service.update(image)

        missing_file_response = self.client.get(
            f"{self.uri}/{image.external_id}/display?filter[width]=1&filter[height]=2"
        )
        unknown_id_response = self.client.get(
            f"{self.uri}/nonexistent123456/display?filter[width]=1&filter[height]=2"
        )

        self.assertEqual(
            missing_file_response.status_code, unknown_id_response.status_code
        )
        self.assertEqual(missing_file_response.content, unknown_id_response.content)
        self.assertEqual(missing_file_response.content, b"")

    def test_display_image_never_returns_404(self):
        """No path on display returns 404 — unknown ids and missing files both map to 403."""
        response = self.client.get(
            f"{self.uri}/nonexistent123456/display?filter[width]=abc"
        )
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_display_image_invalid_dimensions_independent_of_id_existence(self):
        """filter[width]=abc must answer identically for a known and an unknown id."""
        LibraryService().scan()
        image = self.image_service.list()[0]

        known_id_response = self.client.get(
            f"{self.uri}/{image.external_id}/display?filter[width]=abc&filter[height]=100"
        )
        unknown_id_response = self.client.get(
            f"{self.uri}/nonexistent123456/display?filter[width]=abc&filter[height]=100"
        )

        self.assertEqual(known_id_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(known_id_response.status_code, unknown_id_response.status_code)
        self.assertEqual(known_id_response.json(), unknown_id_response.json())

    def test_display_image_invalid_dimensions_issues_no_image_query(self):
        """An invalid-dimension request must not query the Image table."""
        from unittest.mock import patch

        with patch("smplfrm.views.api.v1.images.ImageService.read") as mock_read:
            response = self.client.get(
                f"{self.uri}/nonexistent123456/display?filter[width]=abc"
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            mock_read.assert_not_called()

    def test_display_image_unknown_id_logs_warning_without_file_details(self):
        """The unknown-id 403 emits exactly one WARNING naming the external_id only."""
        with self.assertLogs(
            "smplfrm.views.api.v1.images", level="WARNING"
        ) as captured:
            response = self.client.get(
                f"{self.uri}/nonexistent123456/display?filter[width]=100&filter[height]=100"
            )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(len(captured.records), 1)
        message = captured.records[0].getMessage()
        self.assertIn("nonexistent123456", message)
        self.assertNotIn("file_path", message)
        self.assertNotIn("file_name", message)

    def test_display_image_missing_file_logs_warning_without_file_details(self):
        """The missing-file 403 emits exactly one WARNING naming the external_id only,
        and never the file_path or file_name."""
        LibraryService().scan()
        image = self.image_service.list()[0]
        image.file_path = "/does/Not/Exist.jpg"
        self.image_service.update(image)

        with self.assertLogs(
            "smplfrm.views.api.v1.images", level="WARNING"
        ) as captured:
            response = self.client.get(
                f"{self.uri}/{image.external_id}/display?filter[width]=1&filter[height]=2"
            )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(len(captured.records), 1)
        message = captured.records[0].getMessage()
        self.assertIn(image.external_id, message)
        self.assertNotIn(image.file_path, message)
        self.assertNotIn("Exist.jpg", message)
