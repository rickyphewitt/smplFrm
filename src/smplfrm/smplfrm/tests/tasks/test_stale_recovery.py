"""Tests for stale preload task recovery."""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from smplfrm.celery import app
from smplfrm.models import Task
from smplfrm.models.task import TaskType, Status
from smplfrm.tasks.preload_tasks import recover_stale_preload_tasks


class TestStaleRecoveryRegistration(TestCase):
    """Test that stale recovery task is registered with Celery."""

    def test_stale_recovery_task_can_be_dispatched(self):
        """Verify task can be dispatched without KeyError.

        Regression test for: Received unregistered task of type 'recover_stale_preload_tasks'
        """
        # Verify task is in registry
        self.assertIn("recover_stale_preload_tasks", app.tasks)

        # Verify task signature can be created
        signature = app.signature("recover_stale_preload_tasks")
        self.assertIsNotNone(signature)
        self.assertEqual(signature.name, "recover_stale_preload_tasks")


class TestStaleRecovery(TestCase):
    """Test suite for stale preload task recovery."""

    def test_stale_task_transitions_to_failed(self):
        """Test that stale tasks transition to failed status."""
        now = timezone.now()

        # Create a stale pending task (no update for 11 minutes)
        stale_task = Task.objects.create(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            status=Status.PENDING,
            payload={"fingerprint": "test"},
        )
        # Use update() to bypass auto_now
        Task.objects.filter(external_id=stale_task.external_id).update(
            updated=now - timedelta(minutes=11)
        )
        stale_task.refresh_from_db()

        recover_stale_preload_tasks()

        stale_task.refresh_from_db()
        self.assertEqual(stale_task.status, Status.FAILED)
        self.assertIn("stale", stale_task.error.lower())

    def test_recent_task_not_affected(self):
        """Test that recently updated tasks are not marked stale."""
        now = timezone.now()

        # Create a recent pending task (updated 5 minutes ago)
        recent_task = Task.objects.create(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            status=Status.PENDING,
            payload={"fingerprint": "test"},
        )
        Task.objects.filter(external_id=recent_task.external_id).update(
            updated=now - timedelta(minutes=5)
        )
        recent_task.refresh_from_db()

        recover_stale_preload_tasks()

        recent_task.refresh_from_db()
        self.assertEqual(recent_task.status, Status.PENDING)

    def test_terminal_tasks_not_affected(self):
        """Test that completed/failed tasks are not affected by recovery."""
        now = timezone.now()

        # Create old completed task
        completed_task = Task.objects.create(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            status=Status.COMPLETED,
            payload={"fingerprint": "test"},
        )
        Task.objects.filter(external_id=completed_task.external_id).update(
            updated=now - timedelta(hours=1)
        )
        completed_task.refresh_from_db()

        # Create old failed task
        failed_task = Task.objects.create(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            status=Status.FAILED,
            payload={"fingerprint": "test"},
        )
        Task.objects.filter(external_id=failed_task.external_id).update(
            updated=now - timedelta(hours=1)
        )
        failed_task.refresh_from_db()

        recover_stale_preload_tasks()

        completed_task.refresh_from_db()
        failed_task.refresh_from_db()
        self.assertEqual(completed_task.status, Status.COMPLETED)
        self.assertEqual(failed_task.status, Status.FAILED)

    def test_stale_recovery_emits_one_warning(self):
        """Test that recovery emits exactly one warning per stale task."""
        now = timezone.now()

        stale_task = Task.objects.create(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            status=Status.RUNNING,
            payload={"fingerprint": "test"},
        )
        Task.objects.filter(external_id=stale_task.external_id).update(
            updated=now - timedelta(minutes=15)
        )
        stale_task.refresh_from_db()

        with patch("smplfrm.tasks.preload_tasks.logger") as mock_logger:
            recover_stale_preload_tasks()

            # Should emit exactly one warning
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]

            # Should contain task identity and status
            self.assertIn(stale_task.external_id, warning_msg)
            self.assertIn("running", warning_msg.lower())

    def test_stale_recovery_excludes_sensitive_data(self):
        """Test that recovery warning excludes sensitive payload data."""
        now = timezone.now()

        stale_task = Task.objects.create(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            status=Status.PENDING,
            payload={
                "fingerprint": "test_fingerprint",
                "width": 1920,
                "height": 1080,
                "image_ids": ["secret_img1", "secret_img2"],
            },
        )
        Task.objects.filter(external_id=stale_task.external_id).update(
            updated=now - timedelta(minutes=12)
        )
        stale_task.refresh_from_db()

        with patch("smplfrm.tasks.preload_tasks.logger") as mock_logger:
            recover_stale_preload_tasks()

            warning_msg = mock_logger.warning.call_args[0][0]

            # Should NOT contain payload details
            self.assertNotIn("secret_img1", warning_msg)
            self.assertNotIn("secret_img2", warning_msg)
            self.assertNotIn("1920", warning_msg)
            self.assertNotIn("1080", warning_msg)
            self.assertNotIn("test_fingerprint", warning_msg)

    def test_multiple_stale_tasks_all_recovered(self):
        """Test that multiple stale tasks are all recovered in one pass."""
        now = timezone.now()

        stale_tasks = []
        for i in range(3):
            task = Task.objects.create(
                task_type=TaskType.PRELOAD_IMAGE_CACHE,
                status=Status.PENDING,
                payload={"fingerprint": f"test_{i}"},
            )
            Task.objects.filter(external_id=task.external_id).update(
                updated=now - timedelta(minutes=11 + i)
            )
            task.refresh_from_db()
            stale_tasks.append(task)

        recover_stale_preload_tasks()

        for task in stale_tasks:
            task.refresh_from_db()
            self.assertEqual(task.status, Status.FAILED)

    def test_non_preload_tasks_not_affected(self):
        """Test that stale recovery only affects preload tasks."""
        now = timezone.now()

        # Create stale task of different type
        other_task = Task.objects.create(
            task_type=TaskType.CLEAR_CACHE,
            status=Status.PENDING,
        )
        Task.objects.filter(external_id=other_task.external_id).update(
            updated=now - timedelta(hours=1)
        )
        other_task.refresh_from_db()

        recover_stale_preload_tasks()

        other_task.refresh_from_db()
        self.assertEqual(other_task.status, Status.PENDING)
