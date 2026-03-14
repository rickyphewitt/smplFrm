from django.test import TestCase

from smplfrm.models import Task
from smplfrm.services.task_service import TaskService


class TestTaskService(TestCase):
    """Test suite for TaskService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = TaskService()
        self.task = Task.objects.create(task_type=Task.TaskType.RESCAN_LIBRARY)

    def test_create_task(self):
        """Test creating a task via service."""
        task = self.service.create({"task_type": Task.TaskType.CLEAR_CACHE})

        self.assertEqual(task.task_type, "clear_cache")
        self.assertEqual(task.status, "pending")
        self.assertEqual(task.progress, 0)

    def test_read_task(self):
        """Test reading a task by external ID."""
        retrieved = self.service.read(ext_id=self.task.external_id)
        self.assertEqual(retrieved.external_id, self.task.external_id)

    def test_list_tasks(self):
        """Test listing tasks."""
        Task.objects.create(task_type=Task.TaskType.CLEAR_CACHE)
        tasks = self.service.list()
        self.assertEqual(tasks.count(), 2)

    def test_list_tasks_with_filter(self):
        """Test listing tasks with filter."""
        Task.objects.create(task_type=Task.TaskType.CLEAR_CACHE)
        tasks = self.service.list(task_type=Task.TaskType.RESCAN_LIBRARY)
        self.assertEqual(tasks.count(), 1)

    def test_update_task(self):
        """Test updating a task."""
        self.task.progress = 50
        updated = self.service.update(self.task)

        self.assertEqual(updated.progress, 50)
        self.task.refresh_from_db()
        self.assertEqual(self.task.progress, 50)

    def test_start_task(self):
        """Test starting a task sets status to running."""
        started = self.service.start(self.task)

        self.assertEqual(started.status, "running")
        self.assertEqual(started.progress, 0)

    def test_complete_task(self):
        """Test completing a task sets status and progress."""
        completed = self.service.complete(self.task)

        self.assertEqual(completed.status, "completed")
        self.assertEqual(completed.progress, 100)

    def test_fail_task(self):
        """Test failing a task sets status and error."""
        failed = self.service.fail(self.task, error="Something broke")

        self.assertEqual(failed.status, "failed")
        self.assertEqual(failed.error, "Something broke")

    def test_update_progress(self):
        """Test updating task progress."""
        updated = self.service.update_progress(self.task, 75)
        self.assertEqual(updated.progress, 75)

    def test_update_progress_caps_at_100(self):
        """Test that progress is capped at 100."""
        updated = self.service.update_progress(self.task, 150)
        self.assertEqual(updated.progress, 100)

    def test_delete_not_supported(self):
        """Test that delete raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            self.service.delete(self.task.external_id)

    def test_destroy_not_supported(self):
        """Test that destroy raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            self.service.destroy(self.task.external_id)
