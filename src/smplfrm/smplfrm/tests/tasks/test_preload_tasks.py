"""Tests for preload_image_cache worker task."""

from unittest.mock import patch, MagicMock
import numpy as np

from django.test import TestCase
from django.utils import timezone

from smplfrm.celery import app
from smplfrm.models import Image, Task
from smplfrm.models.task import TaskType, Status
from smplfrm.tasks.preload_tasks import preload_image_cache


class TestPreloadTaskRegistration(TestCase):
    """Test that preload task is registered with Celery."""

    def test_preload_task_can_be_dispatched(self):
        """Verify task can be dispatched without KeyError.

        Regression test for: Received unregistered task of type 'preload_image_cache'
        """
        # Verify task is in registry
        self.assertIn("preload_image_cache", app.tasks)

        # Verify task signature can be created
        signature = app.signature("preload_image_cache", args=("test_id",))
        self.assertIsNotNone(signature)
        self.assertEqual(signature.name, "preload_image_cache")


class TestPreloadImageCache(TestCase):
    """Test suite for preload_image_cache worker."""

    def setUp(self):
        """Set up test fixtures."""
        self.img1 = Image.objects.create(
            name="img1", file_path="/test/img1.jpg", file_name="img1.jpg"
        )
        self.img2 = Image.objects.create(
            name="img2", file_path="/test/img2.jpg", file_name="img2.jpg"
        )
        self.img3 = Image.objects.create(
            name="img3", file_path="/test/img3.jpg", file_name="img3.jpg"
        )

    def test_preload_caches_missing_images(self):
        """Test that preload caches images not already in cache."""
        task = Task.objects.create(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            payload={
                "width": 1920,
                "height": 1080,
                "image_ids": [self.img1.external_id, self.img2.external_id],
                "fingerprint": "test_fp",
            },
        )

        fake_image_data = np.zeros((1080, 1920, 3), dtype=np.uint8)

        with patch("smplfrm.tasks.preload_tasks.CacheService") as mock_cache_cls, patch(
            "smplfrm.tasks.preload_tasks.ImageManipulationService"
        ) as mock_img_svc_cls, patch(
            "smplfrm.tasks.preload_tasks.ImageService"
        ) as mock_img_lookup_cls:

            mock_cache = MagicMock()
            mock_cache_cls.return_value = mock_cache
            mock_cache.read.return_value = None  # Nothing cached

            mock_img_svc = MagicMock()
            mock_img_svc_cls.return_value = mock_img_svc
            mock_img_svc.display.return_value = fake_image_data

            mock_img_lookup = MagicMock()
            mock_img_lookup_cls.return_value = mock_img_lookup
            mock_img_lookup.read.side_effect = [self.img1, self.img2]

            preload_image_cache(task.external_id)

            # Should cache both images
            self.assertEqual(mock_cache.upsert.call_count, 2)

            task.refresh_from_db()
            self.assertEqual(task.status, Status.COMPLETED)
            self.assertEqual(task.progress, 100)

    def test_preload_skips_cached_images(self):
        """Test that preload skips images already in cache."""
        task = Task.objects.create(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            payload={
                "width": 1920,
                "height": 1080,
                "image_ids": [self.img1.external_id, self.img2.external_id],
                "fingerprint": "test_fp",
            },
        )

        with patch("smplfrm.tasks.preload_tasks.CacheService") as mock_cache_cls, patch(
            "smplfrm.tasks.preload_tasks.ImageManipulationService"
        ) as mock_img_svc_cls, patch(
            "smplfrm.tasks.preload_tasks.ImageService"
        ) as mock_img_lookup_cls:

            mock_cache = MagicMock()
            mock_cache_cls.return_value = mock_cache
            mock_cache.read.return_value = b"already_cached"

            mock_img_svc = MagicMock()
            mock_img_svc_cls.return_value = mock_img_svc

            mock_img_lookup = MagicMock()
            mock_img_lookup_cls.return_value = mock_img_lookup
            mock_img_lookup.read.side_effect = [self.img1, self.img2]

            preload_image_cache(task.external_id)

            # Should not cache anything
            mock_cache.upsert.assert_not_called()
            mock_img_svc.display.assert_not_called()

            task.refresh_from_db()
            self.assertEqual(task.status, Status.COMPLETED)

    def test_preload_skips_deleted_images(self):
        """Test that preload skips images deleted after task creation."""
        self.img2.deleted = True
        self.img2.save()

        task = Task.objects.create(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            payload={
                "width": 1920,
                "height": 1080,
                "image_ids": [self.img1.external_id, self.img2.external_id],
                "fingerprint": "test_fp",
            },
        )

        fake_image_data = np.zeros((1080, 1920, 3), dtype=np.uint8)

        with patch("smplfrm.tasks.preload_tasks.CacheService") as mock_cache_cls, patch(
            "smplfrm.tasks.preload_tasks.ImageManipulationService"
        ) as mock_img_svc_cls, patch(
            "smplfrm.tasks.preload_tasks.ImageService"
        ) as mock_img_lookup_cls:

            mock_cache = MagicMock()
            mock_cache_cls.return_value = mock_cache
            mock_cache.read.return_value = None

            mock_img_svc = MagicMock()
            mock_img_svc_cls.return_value = mock_img_svc
            mock_img_svc.display.return_value = fake_image_data

            mock_img_lookup = MagicMock()
            mock_img_lookup_cls.return_value = mock_img_lookup
            # First call succeeds, second raises DoesNotExist
            from django.core.exceptions import ObjectDoesNotExist

            mock_img_lookup.read.side_effect = [self.img1, ObjectDoesNotExist()]

            preload_image_cache(task.external_id)

            # Should only cache img1
            self.assertEqual(mock_cache.upsert.call_count, 1)

            task.refresh_from_db()
            self.assertEqual(task.status, Status.COMPLETED)

    def test_preload_reports_monotonic_progress(self):
        """Test that preload reports progress after each image."""
        task = Task.objects.create(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            payload={
                "width": 1920,
                "height": 1080,
                "image_ids": [
                    self.img1.external_id,
                    self.img2.external_id,
                    self.img3.external_id,
                ],
                "fingerprint": "test_fp",
            },
        )

        fake_image_data = np.zeros((1080, 1920, 3), dtype=np.uint8)
        progress_values = []

        def capture_progress(*args):
            task.refresh_from_db()
            progress_values.append(task.progress)

        with patch("smplfrm.tasks.preload_tasks.CacheService") as mock_cache_cls, patch(
            "smplfrm.tasks.preload_tasks.ImageManipulationService"
        ) as mock_img_svc_cls, patch(
            "smplfrm.tasks.preload_tasks.ImageService"
        ) as mock_img_lookup_cls:

            mock_cache = MagicMock()
            mock_cache_cls.return_value = mock_cache
            mock_cache.read.return_value = None
            mock_cache.upsert.side_effect = capture_progress

            mock_img_svc = MagicMock()
            mock_img_svc_cls.return_value = mock_img_svc
            mock_img_svc.display.return_value = fake_image_data

            mock_img_lookup = MagicMock()
            mock_img_lookup_cls.return_value = mock_img_lookup
            mock_img_lookup.read.side_effect = [self.img1, self.img2, self.img3]

            preload_image_cache(task.external_id)

            # Progress should be monotonically increasing
            self.assertEqual(len(progress_values), 3)
            self.assertTrue(
                all(
                    progress_values[i] <= progress_values[i + 1]
                    for i in range(len(progress_values) - 1)
                )
            )

    def test_preload_completes_at_100(self):
        """Test that preload marks task completed at 100% progress."""
        task = Task.objects.create(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            payload={
                "width": 1920,
                "height": 1080,
                "image_ids": [self.img1.external_id],
                "fingerprint": "test_fp",
            },
        )

        fake_image_data = np.zeros((1080, 1920, 3), dtype=np.uint8)

        with patch("smplfrm.tasks.preload_tasks.CacheService") as mock_cache_cls, patch(
            "smplfrm.tasks.preload_tasks.ImageManipulationService"
        ) as mock_img_svc_cls, patch(
            "smplfrm.tasks.preload_tasks.ImageService"
        ) as mock_img_lookup_cls:

            mock_cache = MagicMock()
            mock_cache_cls.return_value = mock_cache
            mock_cache.read.return_value = None

            mock_img_svc = MagicMock()
            mock_img_svc_cls.return_value = mock_img_svc
            mock_img_svc.display.return_value = fake_image_data

            mock_img_lookup = MagicMock()
            mock_img_lookup_cls.return_value = mock_img_lookup
            mock_img_lookup.read.return_value = self.img1

            preload_image_cache(task.external_id)

            task.refresh_from_db()
            self.assertEqual(task.status, Status.COMPLETED)
            self.assertEqual(task.progress, 100)

    def test_preload_stores_generic_error_on_failure(self):
        """Test that preload stores only generic error message on failure."""
        task = Task.objects.create(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            payload={
                "width": 1920,
                "height": 1080,
                "image_ids": [self.img1.external_id],
                "fingerprint": "test_fp",
            },
        )

        with patch("smplfrm.tasks.preload_tasks.CacheService") as mock_cache_cls, patch(
            "smplfrm.tasks.preload_tasks.ImageService"
        ) as mock_img_lookup_cls:

            mock_cache = MagicMock()
            mock_cache_cls.return_value = mock_cache
            mock_cache.read.side_effect = RuntimeError(
                "Internal connection pool error at line 42"
            )

            mock_img_lookup = MagicMock()
            mock_img_lookup_cls.return_value = mock_img_lookup
            mock_img_lookup.read.return_value = self.img1

            preload_image_cache(task.external_id)

            task.refresh_from_db()
            self.assertEqual(task.status, Status.FAILED)
            # Should contain generic message, not internal details
            self.assertEqual(task.error, "Cache preload failed")
            self.assertNotIn("connection pool", task.error)
            self.assertNotIn("line 42", task.error)

    def test_preload_logs_exception_once(self):
        """Test that preload logs the original exception with traceback exactly once."""
        task = Task.objects.create(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            payload={
                "width": 1920,
                "height": 1080,
                "image_ids": [self.img1.external_id],
                "fingerprint": "test_fp",
            },
        )

        original_error = RuntimeError("Internal connection pool error")

        with patch("smplfrm.tasks.preload_tasks.CacheService") as mock_cache_cls, patch(
            "smplfrm.tasks.preload_tasks.ImageService"
        ) as mock_img_lookup_cls, patch(
            "smplfrm.services.task_reporting_service.logger"
        ) as mock_logger:

            mock_cache = MagicMock()
            mock_cache_cls.return_value = mock_cache
            mock_cache.read.side_effect = original_error

            mock_img_lookup = MagicMock()
            mock_img_lookup_cls.return_value = mock_img_lookup
            mock_img_lookup.read.return_value = self.img1

            preload_image_cache(task.external_id)

            # Verify logger.error was called exactly once with exc_info=True
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            self.assertIn("Task execution error", call_args[0][0])
            self.assertIsInstance(call_args[0][1], RuntimeError)
            self.assertTrue(call_args[1].get("exc_info"))
