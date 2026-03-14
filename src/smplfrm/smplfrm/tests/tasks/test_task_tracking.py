from django.test import TestCase

from smplfrm.models import Task
from smplfrm.services.task_service import TaskService
from smplfrm.tasks.tasks import _run_with_task_tracking


class TestRunWithTaskTracking(TestCase):
    """Test suite for task tracking helper."""

    def setUp(self):
        self.service = TaskService()

    def test_successful_task_completes(self):
        """Test that a successful function marks task as completed."""
        task = Task.objects.create(task_type=Task.TaskType.CLEAR_CACHE)

        _run_with_task_tracking(task.external_id, lambda: None)

        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.COMPLETED)
        self.assertEqual(task.progress, 100)

    def test_failed_task_records_error(self):
        """Test that a failed function marks task as failed with error."""
        task = Task.objects.create(task_type=Task.TaskType.CLEAR_CACHE)

        def failing_fn():
            raise ValueError("test error")

        with self.assertRaises(ValueError):
            _run_with_task_tracking(task.external_id, failing_fn)

        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.FAILED)
        self.assertEqual(task.error, "test error")

    def test_no_task_id_runs_without_tracking(self):
        """Test that None task_id runs function without tracking."""
        called = []
        _run_with_task_tracking(None, lambda: called.append(True))
        self.assertEqual(len(called), 1)

    def test_task_starts_before_running(self):
        """Test that task status is set to running before execution."""
        task = Task.objects.create(task_type=Task.TaskType.RESCAN_LIBRARY)
        statuses = []

        def capture_status():
            task.refresh_from_db()
            statuses.append(task.status)

        _run_with_task_tracking(task.external_id, capture_status)
        self.assertEqual(statuses[0], Task.Status.RUNNING)
