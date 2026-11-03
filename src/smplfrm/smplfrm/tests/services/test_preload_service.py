"""Tests for PreloadService admission and dispatch logic."""

import uuid
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

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
        with (
            patch.object(self.service.cache_service, "read") as mock_read,
            patch("smplfrm.services.preload_service.app") as mock_app,
        ):
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
        with (
            patch.object(self.service.cache_service, "read") as mock_read,
            patch("smplfrm.services.preload_service.app") as mock_app,
        ):
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
        with (
            patch.object(self.service.cache_service, "read") as mock_read,
            patch("smplfrm.services.preload_service.app"),
        ):
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
        with (
            patch.object(self.service.cache_service, "read") as mock_read,
            patch("smplfrm.services.preload_service.app"),
        ):
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


class TestPreloadRetention(TestCase):
    """Test suite for the preload task retention cap."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = PreloadService()
        self.image = Image.objects.create(
            name="img1", file_path="/test/", file_name="img1.jpg"
        )

    def _make_task(
        self,
        task_type=TaskType.PRELOAD_IMAGE_CACHE,
        status=Status.COMPLETED,
        age_minutes=0,
        deleted=False,
    ):
        """Create a task row with an explicit created timestamp.

        created uses auto_now_add, so it cannot be passed to create() and has
        to be set with a queryset update.
        """
        task = Task.objects.create(
            task_type=task_type,
            status=status,
            deleted=deleted,
            payload={"fingerprint": uuid.uuid4().hex},
        )
        Task.objects.filter(pk=task.pk).update(
            created=timezone.now() - timedelta(minutes=age_minutes)
        )
        task.refresh_from_db()
        return task

    def _preload_tasks(self):
        return Task.objects.filter(task_type=TaskType.PRELOAD_IMAGE_CACHE)

    def _create_preload_task(self):
        """Admit one preload task with the cache empty and Celery stubbed."""
        with (
            patch.object(self.service.cache_service, "read", return_value=None),
            patch("smplfrm.services.preload_service.app"),
        ):
            return self.service.create_preload_task(
                [self.image.external_id], 1920, 1080
            )

    def test_creation_trims_preload_tasks_beyond_cap(self):
        """Admitting a task when the cap is already full leaves 10 rows."""
        for age in range(10, 0, -1):
            self._make_task(age_minutes=age)

        task = self._create_preload_task()

        self.assertIsNotNone(task)
        self.assertEqual(self._preload_tasks().count(), 10)
        self.assertTrue(self._preload_tasks().filter(pk=task.pk).exists())

    def test_trim_retains_the_newest_rows(self):
        """The surviving rows are the newest by created, and the trim is idempotent."""
        tasks = [self._make_task(age_minutes=age) for age in range(14, 0, -1)]

        self.assertEqual(self.service._trim_retained_tasks(), 4)

        surviving = set(self._preload_tasks().values_list("pk", flat=True))
        self.assertEqual(surviving, {task.pk for task in tasks[-10:]})

        # Re-running with the count at the cap deletes nothing.
        self.assertEqual(self.service._trim_retained_tasks(), 0)
        self.assertEqual(self._preload_tasks().count(), 10)

    def test_trim_ignores_other_task_types(self):
        """Manual task types are neither counted nor deleted by the trim."""
        for age in range(15, 0, -1):
            self._make_task(age_minutes=age)
        manual_tasks = [
            self._make_task(task_type=task_type, age_minutes=60)
            for task_type in (
                TaskType.RESCAN_LIBRARY,
                TaskType.RESET_IMAGE_COUNT,
                TaskType.CLEAR_CACHE,
            )
        ]

        self.service._trim_retained_tasks()

        self.assertEqual(self._preload_tasks().count(), 10)
        for task in manual_tasks:
            self.assertTrue(Task.objects.filter(pk=task.pk).exists())

    def test_trim_deletes_nothing_below_cap(self):
        """A count below the cap is left alone."""
        for age in range(5, 0, -1):
            self._make_task(age_minutes=age)

        self.assertEqual(self.service._trim_retained_tasks(), 0)
        self.assertEqual(self._preload_tasks().count(), 5)

    def test_running_row_outside_retained_window_survives(self):
        """A running row a worker may still be reading is never hard-deleted."""
        in_flight = self._make_task(status=Status.RUNNING, age_minutes=120)
        for age in range(10, 0, -1):
            self._make_task(age_minutes=age)

        self.service._trim_retained_tasks()

        self.assertTrue(Task.objects.filter(pk=in_flight.pk).exists())
        self.assertEqual(self._preload_tasks().count(), 11)

    def test_pending_row_outside_retained_window_survives(self):
        """A pending row is non-terminal and so is never hard-deleted."""
        queued = self._make_task(status=Status.PENDING, age_minutes=120)
        for age in range(10, 0, -1):
            self._make_task(age_minutes=age)

        self.service._trim_retained_tasks()

        self.assertTrue(Task.objects.filter(pk=queued.pk).exists())
        self.assertEqual(self._preload_tasks().count(), 11)

    def test_recovered_row_is_trimmed_once_terminal(self):
        """Stale recovery marking a row failed makes it eligible for the trim."""
        in_flight = self._make_task(status=Status.RUNNING, age_minutes=120)
        for age in range(10, 0, -1):
            self._make_task(age_minutes=age)

        self.service._trim_retained_tasks()
        Task.objects.filter(pk=in_flight.pk).update(status=Status.FAILED)
        self.service._trim_retained_tasks()

        self.assertFalse(Task.objects.filter(pk=in_flight.pk).exists())
        self.assertEqual(self._preload_tasks().count(), 10)

    def test_soft_deleted_terminal_row_is_hard_deleted(self):
        """A row the user dismissed is removed from the table on the next trim."""
        dismissed = self._make_task(age_minutes=5, deleted=True)
        self._make_task(age_minutes=1)

        self.assertEqual(self.service._trim_retained_tasks(), 1)
        self.assertFalse(Task.objects.filter(pk=dismissed.pk).exists())

    def test_soft_deleted_rows_do_not_consume_retention_slots(self):
        """Dismissed rows do not displace visible rows, even when they are newer."""
        visible = [self._make_task(age_minutes=age) for age in range(19, 9, -1)]
        dismissed = [
            self._make_task(age_minutes=age, deleted=True) for age in (3, 2, 1)
        ]

        self.service._trim_retained_tasks()

        surviving = set(self._preload_tasks().values_list("pk", flat=True))
        self.assertEqual(surviving, {task.pk for task in visible})
        for task in dismissed:
            self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    def test_all_cached_batch_runs_no_trim(self):
        """No row is created for a fully cached batch, so nothing is trimmed."""
        with (
            patch.object(self.service.cache_service, "read", return_value=b"cached"),
            patch.object(self.service, "_trim_retained_tasks") as mock_trim,
        ):
            result = self.service.create_preload_task(
                [self.image.external_id], 1920, 1080
            )

        self.assertIsNone(result)
        mock_trim.assert_not_called()

    def test_duplicate_rejection_runs_no_trim(self):
        """A duplicate fingerprint adds no row, so nothing is trimmed."""
        fingerprint = self.service._compute_fingerprint(
            [self.image.external_id], 1920, 1080
        )
        Task.objects.create(
            task_type=TaskType.PRELOAD_IMAGE_CACHE,
            status=Status.RUNNING,
            payload={"fingerprint": fingerprint},
        )

        with (
            patch.object(self.service.cache_service, "read", return_value=None),
            patch.object(self.service, "_trim_retained_tasks") as mock_trim,
            self.assertRaises(PreloadConflict) as ctx,
        ):
            self.service.create_preload_task([self.image.external_id], 1920, 1080)

        self.assertEqual(ctx.exception.code, "preload_already_in_progress")
        mock_trim.assert_not_called()

    def test_capacity_rejection_runs_no_trim(self):
        """A capacity rejection adds no row, so nothing is trimmed."""
        for _ in range(self.service.MAX_NON_TERMINAL_TASKS):
            self._make_task(status=Status.PENDING)

        with (
            patch.object(self.service.cache_service, "read", return_value=None),
            patch.object(self.service, "_trim_retained_tasks") as mock_trim,
            self.assertRaises(PreloadConflict) as ctx,
        ):
            self.service.create_preload_task([self.image.external_id], 1920, 1080)

        self.assertEqual(ctx.exception.code, "preload_capacity_exceeded")
        mock_trim.assert_not_called()

    def test_trim_failure_does_not_fail_admission(self):
        """A trim error is logged once and the dispatched task is still returned."""
        with (
            patch.object(self.service.cache_service, "read", return_value=None),
            patch("smplfrm.services.preload_service.app"),
            patch.object(
                self.service,
                "_trim_retained_tasks",
                side_effect=RuntimeError("database is locked"),
            ),
        ):
            with self.assertLogs(
                "smplfrm.services.preload_service", level="ERROR"
            ) as captured:
                task = self.service.create_preload_task(
                    [self.image.external_id], 1920, 1080
                )

        self.assertIsNotNone(task)
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())
        self.assertEqual(len(captured.records), 1)
        self.assertEqual(captured.records[0].levelname, "ERROR")
        self.assertIsNotNone(captured.records[0].exc_info)
