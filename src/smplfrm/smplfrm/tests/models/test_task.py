from django.test import TestCase

from smplfrm.models import Task


class TestTask(TestCase):
    """Test suite for Task model."""

    def test_create_task_with_defaults(self):
        """Test creating a task with default values."""
        task = Task.objects.create(task_type=Task.TaskType.RESCAN_LIBRARY)

        self.assertEqual(task.task_type, "rescan_library")
        self.assertEqual(task.status, "pending")
        self.assertEqual(task.progress, 0)
        self.assertEqual(task.error, "")

    def test_task_type_choices(self):
        """Test all valid task type choices."""
        for task_type in Task.TaskType:
            task = Task.objects.create(task_type=task_type)
            task.refresh_from_db()
            self.assertEqual(task.task_type, task_type)

    def test_task_status_choices(self):
        """Test all valid status choices."""
        task = Task.objects.create(task_type=Task.TaskType.CLEAR_CACHE)

        for status in Task.Status:
            task.status = status
            task.save()
            task.refresh_from_db()
            self.assertEqual(task.status, status)

    def test_task_inherits_model_base(self):
        """Test that Task has ModelBase fields."""
        task = Task.objects.create(task_type=Task.TaskType.RESET_IMAGE_COUNT)

        self.assertIsNotNone(task.external_id)
        self.assertIsNotNone(task.created)
        self.assertIsNotNone(task.updated)
        self.assertFalse(task.deleted)

    def test_preload_task_type_exists(self):
        """Test that preload_image_cache task type is available."""
        task = Task.objects.create(task_type=Task.TaskType.PRELOAD_IMAGE_CACHE)
        task.refresh_from_db()
        self.assertEqual(task.task_type, "preload_image_cache")

    def test_payload_nullable(self):
        """Test that payload can store structured task data and defaults to None."""
        # Create task without payload
        task_without_payload = Task.objects.create(task_type=Task.TaskType.CLEAR_CACHE)
        self.assertIsNone(task_without_payload.payload)

        # Create task with payload
        payload = {
            "width": 1920,
            "height": 1080,
            "image_ids": ["abc123", "def456"],
        }
        task_with_payload = Task.objects.create(
            task_type=Task.TaskType.PRELOAD_IMAGE_CACHE, payload=payload
        )
        task_with_payload.refresh_from_db()
        self.assertEqual(task_with_payload.payload, payload)
        self.assertEqual(task_with_payload.payload["width"], 1920)
