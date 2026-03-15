import os

from django.test import TestCase
from django.test.utils import override_settings
from smplfrm.models.task import Task, TaskType
from smplfrm.models.task import TaskType
from smplfrm.services import ImageService, LibraryService, TaskService
from smplfrm.services import LibraryService

test_library = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "library"))
]


@override_settings(SMPL_FRM_LIBRARY_DIRS=test_library)
class TestLibraryService(TestCase):
    def setUp(self):

        self.library_service = LibraryService()
        self.image_service = ImageService()
        self.task_service = TaskService()

    def test_scan(self):
        # verify that as task was created when one is not provided
        old_task_count = self.task_service.list(
            task_type=TaskType.RESCAN_LIBRARY
        ).count()
        self.library_service.scan()

        images = self.image_service.list(deleted=False)

        self.assertIsNotNone(images, "Images should not be None")
        self.assertEqual(len(images), 3, f"Expected 3 images but found {len(images)}")

        # mark images as deleted that do exist on the file system and
        # verify scan marks them as non deleted
        valid_image = images[0]
        valid_image.deleted = True
        valid_image.save()

        # add images that are not present on the filesystem and verify
        # scan marks them as deleteXd
        image_data = {
            "name": "should_be_deleted",
            "file_path": "./filePathDoesNotExist/",
            "file_name": "fileNameDoesNotExist.jpg",
        }
        created_image = self.image_service.create(image_data)
        self.assertFalse(created_image.deleted, "Image should not be deleted")

        self.library_service.scan()
        deleted_image = self.image_service.read(
            ext_id=created_image.external_id, deleted=True
        )
        undeleted_image = self.image_service.read(ext_id=valid_image.external_id)

        # verify metadata exif
        image_meta = undeleted_image.meta
        self.assertIsNotNone(image_meta)
        self.assertIsNotNone(image_meta.exif)

        # verify a new tasks was created, 1 each time scan() is called
        new_task_count = self.task_service.list(
            task_type=TaskType.RESCAN_LIBRARY
        ).count()
        self.assertEqual(
            old_task_count + 2, new_task_count, "A new task should have been created"
        )


@override_settings(SMPL_FRM_LIBRARY_DIRS=test_library)
class TestLibraryScanProgress(TestCase):
    """Test suite for LibraryService.scan progress reporting."""

    def test_scan_calls_reporting_methods(self):
        """Test that scan calls initiate_task, report_task, and complete_task."""
        from unittest.mock import patch, call

        service = LibraryService()

        with patch.object(service, "initiate_task") as mock_init, patch.object(
            service, "report_task"
        ) as mock_report, patch.object(service, "complete_task") as mock_complete:
            service.scan(task_id="test-id")

            # initiate_task called once with task_id and total file count
            mock_init.assert_called_once_with("test-id", 3)

            # report_task called once per image (3 in test library)
            self.assertEqual(mock_report.call_count, 3)
            mock_report.assert_has_calls([call(1), call(2), call(3)])

            # complete_task called once at the end
            mock_complete.assert_called_once()

    def test_scan_starts_task_after_initiation(self):
        """Test that initiate_task sets task status to running."""
        task = Task.objects.create(task_type=TaskType.RESCAN_LIBRARY)
        service = LibraryService()

        from unittest.mock import patch, call

        statuses = []

        with patch.object(
            service,
            "report_task",
            side_effect=lambda p: statuses.append(
                Task.objects.get(external_id=task.external_id).status
            ),
        ):
            service.scan(task_id=task.external_id)

        # Task was running during report_task calls
        self.assertTrue(all(s == "running" for s in statuses))

    def test_scan_marks_task_as_failed_on_error(self):
        """Test that scan calls fail_task with error message when an exception occurs."""
        from unittest.mock import patch

        task = Task.objects.create(task_type=TaskType.RESCAN_LIBRARY)
        service = LibraryService()

        with patch.object(
            service.image_service,
            "create",
            side_effect=RuntimeError("db write failed"),
        ):
            with self.assertRaises(RuntimeError):
                service.scan(task_id=task.external_id)

        task.refresh_from_db()
        self.assertEqual(task.status, "failed")
        self.assertEqual(task.error, "db write failed")
