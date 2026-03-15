from django.test import TestCase

from smplfrm.models.task import Task, TaskType, Status
from smplfrm.services.task_reporting_service import TaskReportingService


class TestTaskReportingService(TestCase):
    """Test suite for TaskReportingService."""

    def setUp(self):
        self.service = TaskReportingService(task_type=TaskType.RESCAN_LIBRARY)

    def test_initiate_task_with_existing_task_id(self):
        """Test initiate_task uses provided task_id."""
        task = Task.objects.create(task_type=TaskType.RESCAN_LIBRARY)
        self.service.initiate_task(task.external_id, 10)

        self.assertEqual(self.service.task_id, task.external_id)
        self.assertEqual(self.service.total, 10)

    def test_initiate_task_creates_task_when_none(self):
        """Test initiate_task creates a new task when task_id is None."""
        self.service.initiate_task(None, 5)

        self.assertIsNotNone(self.service.task_id)
        task = Task.objects.get(external_id=self.service.task_id)
        self.assertEqual(task.task_type, TaskType.RESCAN_LIBRARY)

    def test_report_task_updates_progress_every_5th(self):
        """Test report_task updates progress on every 5th item."""
        task = Task.objects.create(task_type=TaskType.RESCAN_LIBRARY)
        self.service.initiate_task(task.external_id, 20)

        self.service.report_task(5)
        task.refresh_from_db()
        self.assertEqual(task.progress, 25)

        self.service.report_task(10)
        task.refresh_from_db()
        self.assertEqual(task.progress, 50)

    def test_report_task_skips_non_5th(self):
        """Test report_task does not update on non-5th items."""
        task = Task.objects.create(task_type=TaskType.RESCAN_LIBRARY)
        self.service.initiate_task(task.external_id, 20)

        self.service.report_task(3)
        task.refresh_from_db()
        self.assertEqual(task.progress, 0)

    def test_report_task_updates_on_last_item(self):
        """Test report_task updates when processed equals total."""
        task = Task.objects.create(task_type=TaskType.RESCAN_LIBRARY)
        self.service.initiate_task(task.external_id, 7)

        self.service.report_task(7)
        task.refresh_from_db()
        self.assertEqual(task.progress, 100)

    def test_complete_task(self):
        """Test complete_task sets progress to 100 and status to completed."""
        task = Task.objects.create(task_type=TaskType.RESCAN_LIBRARY)
        self.service.initiate_task(task.external_id, 10)

        self.service.complete_task()
        task.refresh_from_db()
        self.assertEqual(task.progress, 100)
        self.assertEqual(task.status, Status.COMPLETED)
