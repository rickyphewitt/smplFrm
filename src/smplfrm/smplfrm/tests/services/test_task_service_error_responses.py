"""
Tests for service layer error handling and sanitization.

These tests verify that service operations (library, image, cache) properly
sanitize error messages when calling fail_task(), ensuring no internal
implementation details are exposed to clients while preserving full error
information in server-side logs for debugging.
"""

from django.test import TestCase
from unittest.mock import patch
from smplfrm.services import LibraryService, ImageService, CacheService
from smplfrm.models.task import Task, TaskType


class TestLibraryServiceErrorResponses(TestCase):
    """Test that LibraryService.scan() sanitizes error messages."""

    def test_scan_sanitizes_error_message_on_exception(self):
        """Test that scan() calls fail_task with a sanitized message, not str(e)."""
        service = LibraryService()
        task = Task.objects.create(task_type=TaskType.RESCAN_LIBRARY)

        # Mock image_service.create to raise an exception with sensitive details
        sensitive_error = "UNIQUE constraint failed: smplfrm_image.file_path"

        with patch.object(
            service.image_service, "create", side_effect=RuntimeError(sensitive_error)
        ):
            with patch.object(service, "fail_task") as mock_fail_task:
                with self.assertRaises(RuntimeError):
                    service.scan(task_id=task.external_id)

                # Verify fail_task was called with a sanitized message
                mock_fail_task.assert_called_once()
                error_message = mock_fail_task.call_args[0][0]

                # Assert the error message is sanitized (generic)
                self.assertIn("operation failed", error_message.lower())

                # Assert the error message does NOT contain sensitive details
                self.assertNotIn("UNIQUE constraint", error_message)
                self.assertNotIn("smplfrm_image", error_message)
                self.assertNotIn("file_path", error_message)


class TestImageServiceErrorResponses(TestCase):
    """Test that ImageService.reset_all_view_count() sanitizes error messages."""

    def test_reset_all_view_count_sanitizes_error_message_on_exception(self):
        """Test that reset_all_view_count() calls fail_task with a sanitized message."""
        from smplfrm.models import Image

        service = ImageService()
        task = Task.objects.create(task_type=TaskType.RESET_IMAGE_COUNT)

        # Create a test image
        test_image = Image.objects.create(
            name="test.jpg", file_path="/test/path.jpg", file_name="test.jpg"
        )

        # Mock the save method to raise an exception with sensitive details
        sensitive_error = "connection to database 'smplfrm_prod' failed: timeout"

        with patch.object(Image, "save", side_effect=RuntimeError(sensitive_error)):
            with patch.object(service, "fail_task") as mock_fail_task:
                with self.assertRaises(RuntimeError):
                    service.reset_all_view_count(task_id=task.external_id)

                # Verify fail_task was called with a sanitized message
                mock_fail_task.assert_called_once()
                error_message = mock_fail_task.call_args[0][0]

                # Assert the error message is sanitized (generic)
                self.assertIn("operation failed", error_message.lower())

                # Assert the error message does NOT contain sensitive details
                self.assertNotIn("connection to database", error_message)
                self.assertNotIn("smplfrm_prod", error_message)
                self.assertNotIn("timeout", error_message)


class TestCacheServiceErrorResponses(TestCase):
    """Test that CacheService.clear() sanitizes error messages."""

    def test_clear_sanitizes_error_message_on_exception(self):
        """Test that clear() calls fail_task with a sanitized message, not str(e)."""
        service = CacheService()
        task = Task.objects.create(task_type=TaskType.CLEAR_CACHE)

        # Mock cache.clear() to raise an exception with sensitive details
        sensitive_error = "Redis connection failed: ECONNREFUSED 10.0.1.5:6379"

        with patch.object(
            service.cache, "clear", side_effect=RuntimeError(sensitive_error)
        ):
            with patch.object(service, "fail_task") as mock_fail_task:
                with self.assertRaises(RuntimeError):
                    service.clear(task_id=task.external_id)

                # Verify fail_task was called with a sanitized message
                mock_fail_task.assert_called_once()
                error_message = mock_fail_task.call_args[0][0]

                # Assert the error message is sanitized (generic)
                self.assertIn("operation failed", error_message.lower())

                # Assert the error message does NOT contain sensitive details
                self.assertNotIn("Redis", error_message)
                self.assertNotIn("ECONNREFUSED", error_message)
                self.assertNotIn("10.0.1.5", error_message)
                self.assertNotIn("6379", error_message)
