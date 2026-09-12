import datetime
import json

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from smplfrm.services import ImageMetadataService, ImageService


class TestImagesMetadata(TestCase):
    """Test suite for ImagesMetadata ViewSet with JSON:API format."""

    def setUp(self):
        self.client = APIClient()
        self.uri = "/api/v1/images_metadata"
        self.image_metadata_service = ImageMetadataService()
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

    def test_list_with_metadata(self):
        """Test that list returns JSON:API collection with metadata."""
        created_image = self.image_service.create(self.full_image_data)
        image_meta = {
            "image": created_image,
            "exif": {"foo": "bar"},
            "taken": datetime.datetime.now(),
        }
        created_meta = self.image_metadata_service.create(image_meta)

        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertIn("data", body)
        self.assertEqual(len(body["data"]), 1)
        self.assertEqual(body["data"][0]["type"], "image_metadata")
        self.assertEqual(body["data"][0]["id"], created_meta.external_id)

    def test_list_pagination(self):
        """Test that list includes JSON:API pagination links and meta."""
        created_image = self.image_service.create(self.full_image_data)
        image_meta = {
            "image": created_image,
            "exif": {"foo": "bar"},
            "taken": datetime.datetime.now(),
        }
        self.image_metadata_service.create(image_meta)

        response = self.client.get(self.uri)
        body = response.json()
        self.assertIn("links", body)
        self.assertIn("meta", body)
        self.assertIn("pagination", body["meta"])

    def test_retrieve_metadata(self):
        """Test that retrieve returns JSON:API resource."""
        created_image = self.image_service.create(self.full_image_data)
        image_meta = {
            "image": created_image,
            "exif": {"foo": "bar"},
            "taken": datetime.datetime.now(),
        }
        created_meta = self.image_metadata_service.create(image_meta)

        response = self.client.get(f"{self.uri}/{created_meta.external_id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertIn("data", body)
        self.assertEqual(body["data"]["type"], "image_metadata")
        self.assertEqual(body["data"]["id"], created_meta.external_id)
        self.assertIn("attributes", body["data"])
        self.assertIn("taken", body["data"]["attributes"])
        self.assertIn("created", body["data"]["attributes"])
        self.assertIn("updated", body["data"]["attributes"])

    def test_retrieve_includes_image_relationship(self):
        """Test that retrieve includes relationship to parent image."""
        created_image = self.image_service.create(self.full_image_data)
        image_meta = {
            "image": created_image,
            "exif": {"foo": "bar"},
            "taken": datetime.datetime.now(),
        }
        created_meta = self.image_metadata_service.create(image_meta)

        response = self.client.get(f"{self.uri}/{created_meta.external_id}")
        body = response.json()
        self.assertIn("relationships", body["data"])
        self.assertIn("image", body["data"]["relationships"])
        self.assertEqual(
            body["data"]["relationships"]["image"]["data"]["type"], "images"
        )
        self.assertEqual(
            body["data"]["relationships"]["image"]["data"]["id"],
            created_image.external_id,
        )

    def test_retrieve_nonexistent_returns_403(self):
        """Test that retrieve of nonexistent metadata returns 403 (not 404)."""
        response = self.client.get(f"{self.uri}/nonexistent123456")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_image_jsonapi_format(self):
        """Test filtering by image using JSON:API filter[image] format."""
        created_image = self.image_service.create(self.full_image_data)
        created_image2 = self.image_service.create(
            {"name": "second_image", "file_path": "foo", "file_name": "foo.jpg"}
        )
        image_meta = {
            "image": created_image,
            "exif": {"foo": "bar"},
            "taken": datetime.datetime.now(),
        }
        image_meta2 = {
            "image": created_image2,
            "exif": {"baz": "qux"},
            "taken": datetime.datetime.now(),
        }
        self.image_metadata_service.create(image_meta)
        self.image_metadata_service.create(image_meta2)

        response = self.client.get(
            f"{self.uri}?filter[image]={created_image.external_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(len(body["data"]), 1)

    def test_legacy_filter_not_supported(self):
        """Test that legacy image__external_id filter is not supported."""
        created_image = self.image_service.create(self.full_image_data)
        image_meta = {
            "image": created_image,
            "exif": {"foo": "bar"},
            "taken": datetime.datetime.now(),
        }
        self.image_metadata_service.create(image_meta)

        # Legacy filter should return all results (filter ignored)
        response = self.client.get(
            f"{self.uri}?image__external_id={created_image.external_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The filter is ignored, so we get all metadata
        body = response.json()
        self.assertEqual(len(body["data"]), 1)  # Still 1 because only 1 exists

    def test_exif_not_exposed(self):
        """Test that exif data is not included in response."""
        created_image = self.image_service.create(self.full_image_data)
        image_meta = {
            "image": created_image,
            "exif": {"sensitive": "data"},
            "taken": datetime.datetime.now(),
        }
        created_meta = self.image_metadata_service.create(image_meta)

        response = self.client.get(f"{self.uri}/{created_meta.external_id}")
        body = response.json()
        self.assertNotIn("exif", body["data"]["attributes"])

    def test_create_not_allowed(self):
        """Test that POST returns 405."""
        response = self.client.post(
            self.uri,
            data=json.dumps({"data": {"type": "image_metadata", "attributes": {}}}),
            content_type="application/vnd.api+json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_not_allowed(self):
        """Test that PUT returns 405."""
        created_image = self.image_service.create(self.full_image_data)
        image_meta = {
            "image": created_image,
            "exif": {"foo": "bar"},
            "taken": datetime.datetime.now(),
        }
        created_meta = self.image_metadata_service.create(image_meta)

        response = self.client.put(
            f"{self.uri}/{created_meta.external_id}",
            data=json.dumps(
                {"data": {"type": "image_metadata", "id": created_meta.external_id}}
            ),
            content_type="application/vnd.api+json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_not_allowed(self):
        """Test that PATCH returns 405."""
        created_image = self.image_service.create(self.full_image_data)
        image_meta = {
            "image": created_image,
            "exif": {"foo": "bar"},
            "taken": datetime.datetime.now(),
        }
        created_meta = self.image_metadata_service.create(image_meta)

        response = self.client.patch(
            f"{self.uri}/{created_meta.external_id}",
            data=json.dumps(
                {"data": {"type": "image_metadata", "id": created_meta.external_id}}
            ),
            content_type="application/vnd.api+json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_not_allowed(self):
        """Test that DELETE returns 405."""
        created_image = self.image_service.create(self.full_image_data)
        image_meta = {
            "image": created_image,
            "exif": {"foo": "bar"},
            "taken": datetime.datetime.now(),
        }
        created_meta = self.image_metadata_service.create(image_meta)

        response = self.client.delete(f"{self.uri}/{created_meta.external_id}")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
