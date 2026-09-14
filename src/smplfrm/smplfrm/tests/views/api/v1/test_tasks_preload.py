"""Tests for preload task creation through task API."""

from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.test import APIClient

from smplfrm.models import Image, Task
from smplfrm.models.task import TaskType, Status
from smplfrm.services.preload_service import PreloadConflict


class TestPreloadTaskCreation(TestCase):
    """Test suite for preload task creation via API."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.img1 = Image.objects.create(
            name="img1", file_path="/test/", file_name="img1.jpg"
        )
        self.img2 = Image.objects.create(
            name="img2", file_path="/test/", file_name="img2.jpg"
        )

    def test_valid_preload_request_creates_task(self):
        """Test that valid preload request creates task."""
        payload = {
            "data": {
                "type": "preload_image_cache_tasks",
                "attributes": {
                    "image_ids": [self.img1.external_id, self.img2.external_id],
                    "width": 1920,
                    "height": 1080,
                },
            }
        }

        with patch(
            "smplfrm.services.preload_service.CacheService"
        ) as mock_cache_cls, patch("smplfrm.services.preload_service.app") as mock_app:
            mock_cache = MagicMock()
            mock_cache_cls.return_value = mock_cache
            mock_cache.read.return_value = None  # Nothing cached

            response = self.client.post(
                "/api/v1/tasks",
                payload,
                HTTP_ACCEPT="application/vnd.api+json",
                content_type="application/vnd.api+json",
            )

            self.assertEqual(response.status_code, 201)
            data = response.json()
            self.assertEqual(data["data"]["type"], "preload_image_cache_tasks")

            # Verify Celery task was dispatched
            mock_app.send_task.assert_called_once()

    def test_preload_conflict_returns_409(self):
        """Test that preload conflict returns 409 with appropriate code."""
        # Create 5 non-terminal preload tasks to exceed capacity
        for i in range(5):
            Task.objects.create(
                task_type=TaskType.PRELOAD_IMAGE_CACHE,
                status=Status.PENDING,
                payload={"fingerprint": f"unique_{i}"},
            )

        payload = {
            "data": {
                "type": "preload_image_cache_tasks",
                "attributes": {
                    "image_ids": [self.img1.external_id],
                    "width": 1920,
                    "height": 1080,
                },
            }
        }

        with patch("smplfrm.services.preload_service.CacheService") as mock_cache_cls:
            mock_cache = MagicMock()
            mock_cache_cls.return_value = mock_cache
            mock_cache.read.return_value = None

            response = self.client.post(
                "/api/v1/tasks",
                payload,
                HTTP_ACCEPT="application/vnd.api+json",
                content_type="application/vnd.api+json",
            )

            self.assertEqual(response.status_code, 409)
            data = response.json()
            self.assertEqual(data["errors"][0]["code"], "preload_capacity_exceeded")

    def test_invalid_dimensions_rejected(self):
        """Test that invalid dimensions are rejected with 400."""
        payload = {
            "data": {
                "type": "preload_image_cache_tasks",
                "attributes": {
                    "image_ids": [self.img1.external_id],
                    "width": 5000,  # Exceeds maximum
                    "height": 1080,
                },
            }
        }

        response = self.client.post(
            "/api/v1/tasks",
            payload,
            HTTP_ACCEPT="application/vnd.api+json",
            content_type="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.data)

    def test_excessive_batch_rejected(self):
        """Test that batch exceeding 5 images is rejected."""
        payload = {
            "data": {
                "type": "preload_image_cache_tasks",
                "attributes": {
                    "image_ids": ["id1", "id2", "id3", "id4", "id5", "id6"],
                    "width": 1920,
                    "height": 1080,
                },
            }
        }

        response = self.client.post(
            "/api/v1/tasks",
            payload,
            HTTP_ACCEPT="application/vnd.api+json",
            content_type="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.data)

    def test_all_cached_returns_204(self):
        """Test that fully cached batch returns 204 No Content."""
        payload = {
            "data": {
                "type": "preload_image_cache_tasks",
                "attributes": {
                    "image_ids": [self.img1.external_id, self.img2.external_id],
                    "width": 1920,
                    "height": 1080,
                },
            }
        }

        with patch("smplfrm.services.preload_service.CacheService") as mock_cache_cls:
            mock_cache = MagicMock()
            mock_cache_cls.return_value = mock_cache
            mock_cache.read.return_value = b"cached_data"  # All cached

            response = self.client.post(
                "/api/v1/tasks",
                payload,
                HTTP_ACCEPT="application/vnd.api+json",
                content_type="application/vnd.api+json",
            )

            self.assertEqual(response.status_code, 204)
            # 204 responses have no body
            self.assertEqual(response.content, b"")
