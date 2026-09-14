"""Tests for PreloadService admission and dispatch logic."""

import hashlib
from unittest.mock import patch, MagicMock

from django.test import TestCase

from smplfrm.models import Image, Task
from smplfrm.models.task import TaskType, Status
from smplfrm.services.preload_service import PreloadService, PreloadConflict


class TestPreloadService(TestCase):
    """Test suite for PreloadService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = PreloadService()
        self.image1 = Image.objects.create(
            name="img1", file_path="/test/", file_name="img1.jpg"
        )
        self.image2 = Image.objects.create(
            name="img2", file_path="/test/", file_name="img2.jpg"
        )
        self.image3 = Image.objects.create(
            name="img3", file_path="/test/", file_name="img3.jpg"
        )

    def test_all_cached_skips_task_creation(self):
        """Test that fully cached batch skips task creation."""
        # Patch the CacheService.read method directly on the service instance
        with patch.object(self.service.cache_service, "read") as mock_read:
            mock_read.return_value = b"cached_data"

            result = self.service.create_preload_task(
                [self.image1.external_id, self.image2.external_id], 1920, 1080
            )

            self.assertIsNone(result)
            # No task should be created
            self.assertEqual(
                Task.objects.filter(task_type=TaskType.PRELOAD_IMAGE_CACHE).count(), 0
            )

    def test_duplicate_in_flight_returns_409(self):
        """Test that duplicate in-flight work returns conflict."""
        # Create a running preload task with matching fingerprint
        payload = {
            "width": 1920,
            "height": 1080,
            "image_ids": [self.image1.external_id, self.image2.external_id],
            "fingerprint": self.service._compute_fingerprint(
                [self.image1.external_id, self.image2.external_id], 1920, 1080
            ),
        }
        Task.objects.create(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            status=Status.RUNNING,
            payload=payload,
        )

        # Mock cache to report nothing cached
        with patch.object(self.service.cache_service, "read") as mock_read:
            mock_read.return_value = None

            with self.assertRaises(PreloadConflict) as ctx:
                self.service.create_preload_task(
                    [self.image1.external_id, self.image2.external_id], 1920, 1080
                )

            self.assertEqual(ctx.exception.code, "preload_already_in_progress")

    def test_capacity_exceeded_returns_409(self):
        """Test that exceeding 5 non-terminal tasks returns conflict."""
        # Create 5 non-terminal preload tasks
        for i in range(5):
            Task.objects.create(
                task_type=TaskType.PRELOAD_IMAGE_CACHE,
                status=Status.PENDING,
                payload={"fingerprint": f"unique_{i}"},
            )

        # Mock cache to report nothing cached
        with patch.object(self.service.cache_service, "read") as mock_read:
            mock_read.return_value = None

            with self.assertRaises(PreloadConflict) as ctx:
                self.service.create_preload_task([self.image1.external_id], 1920, 1080)

            self.assertEqual(ctx.exception.code, "preload_capacity_exceeded")

    def test_fifth_concurrent_accepted(self):
        """Test that the 5th concurrent task is accepted."""
        # Create 4 non-terminal preload tasks
        for i in range(4):
            Task.objects.create(
                task_type=TaskType.PRELOAD_IMAGE_CACHE,
                status=Status.PENDING,
                payload={"fingerprint": f"unique_{i}"},
            )

        # Mock cache and celery
        with patch.object(self.service.cache_service, "read") as mock_read, patch(
            "smplfrm.services.preload_service.app"
        ) as mock_app:
            mock_read.return_value = None

            task = self.service.create_preload_task(
                [self.image1.external_id], 1920, 1080
            )

            self.assertIsNotNone(task)
            self.assertEqual(task.task_type, TaskType.PRELOAD_IMAGE_CACHE)
            mock_app.send_task.assert_called_once()

    def test_sixth_concurrent_rejected(self):
        """Test that the 6th concurrent task is rejected."""
        # Create 5 non-terminal preload tasks
        for i in range(5):
            Task.objects.create(
                task_type=TaskType.PRELOAD_IMAGE_CACHE,
                status=Status.PENDING,
                payload={"fingerprint": f"unique_{i}"},
            )

        # Mock cache
        with patch.object(self.service.cache_service, "read") as mock_read:
            mock_read.return_value = None

            with self.assertRaises(PreloadConflict) as ctx:
                self.service.create_preload_task([self.image1.external_id], 1920, 1080)

            self.assertEqual(ctx.exception.code, "preload_capacity_exceeded")

    def test_terminal_releases_slot(self):
        """Test that terminal tasks don't count against capacity."""
        # Create 5 terminal preload tasks
        for i in range(5):
            Task.objects.create(
                task_type=TaskType.PRELOAD_IMAGE_CACHE,
                status=Status.COMPLETED,
                payload={"fingerprint": f"unique_{i}"},
            )

        # Mock cache and celery
        with patch.object(self.service.cache_service, "read") as mock_read, patch(
            "smplfrm.services.preload_service.app"
        ) as mock_app:
            mock_read.return_value = None

            task = self.service.create_preload_task(
                [self.image1.external_id], 1920, 1080
            )

            self.assertIsNotNone(task)
            # Terminal tasks shouldn't prevent new task creation
            mock_app.send_task.assert_called_once()

    def test_invalid_image_id_skipped_without_error(self):
        """Test that invalid image IDs are skipped during payload construction."""
        # Mock cache and celery
        with patch.object(self.service.cache_service, "read") as mock_read, patch(
            "smplfrm.services.preload_service.app"
        ) as mock_app:
            mock_read.return_value = None

            # Include a nonexistent image ID
            task = self.service.create_preload_task(
                [self.image1.external_id, "nonexistent_id", self.image2.external_id],
                1920,
                1080,
            )

            self.assertIsNotNone(task)
            # Payload should only contain valid IDs
            payload = task.payload
            self.assertEqual(len(payload["image_ids"]), 2)
            self.assertIn(self.image1.external_id, payload["image_ids"])
            self.assertIn(self.image2.external_id, payload["image_ids"])
            self.assertNotIn("nonexistent_id", payload["image_ids"])

    def test_fingerprint_computation(self):
        """Test that work fingerprint is deterministic and order-preserving."""
        fp1 = self.service._compute_fingerprint(["abc", "def"], 1920, 1080)
        fp2 = self.service._compute_fingerprint(["abc", "def"], 1920, 1080)
        fp3 = self.service._compute_fingerprint(["def", "abc"], 1920, 1080)
        fp4 = self.service._compute_fingerprint(["abc", "def"], 1921, 1080)

        # Same inputs should produce same fingerprint
        self.assertEqual(fp1, fp2)
        # Different order should produce different fingerprint
        self.assertNotEqual(fp1, fp3)
        # Different dimensions should produce different fingerprint
        self.assertNotEqual(fp1, fp4)

    def test_creates_execution_payload(self):
        """Test that task is created with proper execution payload."""
        # Mock cache and celery
        with patch.object(self.service.cache_service, "read") as mock_read, patch(
            "smplfrm.services.preload_service.app"
        ) as mock_app:
            mock_read.return_value = None

            task = self.service.create_preload_task(
                [self.image1.external_id, self.image2.external_id], 1920, 1080
            )

            self.assertIsNotNone(task.payload)
            payload = task.payload
            self.assertEqual(payload["width"], 1920)
            self.assertEqual(payload["height"], 1080)
            self.assertEqual(len(payload["image_ids"]), 2)
            self.assertIn("fingerprint", payload)
