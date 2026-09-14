from django.test import TestCase
from django.db.models import ObjectDoesNotExist

from smplfrm.models import Image
from smplfrm.services import ImageService


class TestImageService(TestCase):
    """Test suite for ImageService."""

    def setUp(self):
        """Set up test fixtures."""
        self.image_service = ImageService()
        self.full_image_data = {
            "name": "foo",
            "file_path": "./nested/file/",
            "file_name": "image.jpg",
        }

    def test_create_get_delete_image(self):
        """Test creating, retrieving, updating, and deleting an image."""
        created_image = self.image_service.create(self.full_image_data)
        self._assert_image(created_image)

        # get image from db by external id
        retrieved_image = self.image_service.read(ext_id=created_image.external_id)
        self._assert_image(retrieved_image)
        self.assertEqual(
            created_image.external_id,
            retrieved_image.external_id,
            "External Ids should match!",
        )

        # update image
        retrieved_image.name = "bar"
        updated_image = self.image_service.update(retrieved_image)
        self.assertEqual(updated_image.name, retrieved_image.name, "Name not set.")
        self.assertFalse(updated_image.deleted, "Image should not be deleted")

        # soft delete image
        self.image_service.delete(updated_image.external_id)
        # assert you can't read the image by default
        self.assertRaises(
            ObjectDoesNotExist, self.image_service.read, updated_image.external_id
        )
        # assert you can still pull the image when looking for deleted objects
        soft_deleted_image = self.image_service.read(
            updated_image.external_id, deleted=True
        )
        self.assertEqual(soft_deleted_image.name, updated_image.name, "Name not set.")
        self.assertTrue(soft_deleted_image.deleted, "Image should be deleted")

    def test_next(self):
        """Test retrieving next image based on view count."""
        created_image = self.image_service.create(self.full_image_data)
        self._assert_image(created_image)
        retrieved_image = self.image_service.read(ext_id=created_image.external_id)

        view_count_before_next = retrieved_image.view_count
        image = self.image_service.get_next()[0]

        retrieved_image = self.image_service.read(ext_id=created_image.external_id)
        # assert the view count remains the same, this is updated on display image
        self.assertEqual(view_count_before_next, image.view_count)

        # manually increment to ensure the next call gets the 'next image'
        self.image_service.increment_view_count(retrieved_image)

        # create second image and ensure its called 'next'
        second_image_data = {
            "name": "second-foo",
            "file_path": "/second/image/file/",
            "file_name": "second_image.jpg",
        }
        second_image = self.image_service.create(second_image_data)
        image = self.image_service.get_next()[0]

        self.assertEqual(second_image.external_id, image.external_id)

    def _assert_image(self, image, name="name"):
        """Assert that image has expected attributes.

        Args:
            image: Image instance to validate
            name: Key name for the name field in test data
        """
        self.assertIsNotNone(image.external_id, "External Id should be set on Create.")
        self.assertIsNotNone(image.created, "Created Datetime not set.")
        self.assertIsNotNone(image.updated, "Updated Datetime not set.")
        self.assertEqual(image.name, self.full_image_data[name], "Name not set.")
        self.assertEqual(
            image.file_path, self.full_image_data["file_path"], "File_path not set."
        )
        self.assertEqual(
            image.file_name, self.full_image_data["file_name"], "File_name not set."
        )

    def test_reset_all_view_count(self):
        """Test that reset_all_view_count resets all image view counts."""
        image1 = self.image_service.create(self.full_image_data)
        image2 = self.image_service.create(
            {"name": "bar", "file_path": "/other/", "file_name": "bar.jpg"}
        )
        self.image_service.increment_view_count(image1)
        self.image_service.increment_view_count(image1)
        self.image_service.increment_view_count(image2)

        self.image_service.reset_all_view_count()

        image1.refresh_from_db()
        image2.refresh_from_db()
        self.assertEqual(image1.view_count, 0)
        self.assertEqual(image2.view_count, 0)

    def test_reset_all_view_count_calls_reporting_methods(self):
        """Test that reset calls initiate_task, report_task, and complete_task."""
        from unittest.mock import patch, call

        self.image_service.create(self.full_image_data)
        self.image_service.create(
            {"name": "bar", "file_path": "/other/", "file_name": "bar.jpg"}
        )

        with patch.object(
            self.image_service, "initiate_task"
        ) as mock_init, patch.object(
            self.image_service, "report_task"
        ) as mock_report, patch.object(
            self.image_service, "complete_task"
        ) as mock_complete:
            self.image_service.reset_all_view_count(task_id="test-id")

            mock_init.assert_called_once_with("test-id", 2)
            self.assertEqual(mock_report.call_count, 2)
            mock_report.assert_has_calls([call(1), call(2)])
            mock_complete.assert_called_once()

    def test_reset_all_view_count_starts_task(self):
        """Test that task status is running during reset execution."""
        from unittest.mock import patch
        from smplfrm.models.task import Task, TaskType

        task = Task.objects.create(task_type=TaskType.RESET_IMAGE_COUNT)
        self.image_service.create(self.full_image_data)

        statuses = []
        with patch.object(
            self.image_service,
            "report_task",
            side_effect=lambda p: statuses.append(
                Task.objects.get(external_id=task.external_id).status
            ),
        ):
            self.image_service.reset_all_view_count(task_id=task.external_id)

        self.assertTrue(all(s == "running" for s in statuses))

    def test_reset_all_view_count_marks_failed_on_error(self):
        """Test that task is marked failed when reset encounters an error."""
        from unittest.mock import patch
        from smplfrm.models.task import Task, TaskType

        task = Task.objects.create(task_type=TaskType.RESET_IMAGE_COUNT)
        self.image_service.create(self.full_image_data)

        with patch.object(Image, "save", side_effect=RuntimeError("save failed")):
            with self.assertRaises(RuntimeError):
                self.image_service.reset_all_view_count(task_id=task.external_id)

        task.refresh_from_db()
        self.assertEqual(task.status, "failed")
        self.assertEqual(task.error, "Image count reset operation failed")

    def test_reset_all_view_count_logs_original_exception(self):
        """Test that reset logs the original exception with exc_info=True."""
        from unittest.mock import patch
        from smplfrm.models.task import Task, TaskType

        task = Task.objects.create(task_type=TaskType.RESET_IMAGE_COUNT)
        self.image_service.create(self.full_image_data)

        with patch.object(
            Image, "save", side_effect=RuntimeError("save failed")
        ), patch("smplfrm.services.task_reporting_service.logger") as mock_logger:
            with self.assertRaises(RuntimeError):
                self.image_service.reset_all_view_count(task_id=task.external_id)

            # Verify logger.error was called with the original exception and exc_info=True
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            self.assertIn("Task execution error", call_args[0][0])
            self.assertIsInstance(call_args[0][1], RuntimeError)
            self.assertEqual(str(call_args[0][1]), "save failed")
            self.assertTrue(call_args[1].get("exc_info"))

    def test_reset_all_view_count_does_not_store_internal_details(self):
        """Test that reset does NOT store internal error details in task failure record."""
        from unittest.mock import patch
        from smplfrm.models.task import Task, TaskType

        task = Task.objects.create(task_type=TaskType.RESET_IMAGE_COUNT)
        self.image_service.create(self.full_image_data)

        # Use a realistic internal error message with sensitive details
        internal_error = RuntimeError(
            "Database connection pool exhausted at connection.py:156 - max_connections=100"
        )

        with patch.object(Image, "save", side_effect=internal_error):
            with self.assertRaises(RuntimeError):
                self.image_service.reset_all_view_count(task_id=task.external_id)

        task.refresh_from_db()
        # Verify the task error contains only the sanitized message
        self.assertEqual(task.error, "Image count reset operation failed")
        # Verify internal details are NOT in the task error
        self.assertNotIn("connection pool", task.error)
        self.assertNotIn("connection.py", task.error)
        self.assertNotIn("max_connections", task.error)

    def test_display_priority_sort_order(self):
        """Test that display_priority profile orders by view_count ASC, created DESC, external_id ASC."""
        from datetime import timedelta
        from django.utils import timezone

        now = timezone.now()

        # Create images with varying view counts and creation times
        img1 = self.image_service.create(
            {
                "name": "img1",
                "file_path": "/test/",
                "file_name": "img1.jpg",
            }
        )
        img1.view_count = 5
        img1.created = now - timedelta(hours=3)
        img1.save()

        img2 = self.image_service.create(
            {
                "name": "img2",
                "file_path": "/test/",
                "file_name": "img2.jpg",
            }
        )
        img2.view_count = 2
        img2.created = now - timedelta(hours=1)
        img2.save()

        img3 = self.image_service.create(
            {
                "name": "img3",
                "file_path": "/test/",
                "file_name": "img3.jpg",
            }
        )
        img3.view_count = 2
        img3.created = now - timedelta(hours=2)
        img3.save()

        # Get ordered images
        ordered = list(self.image_service.get_ordered_images("display_priority"))

        # Expected order: img2 (view=2, newer), img3 (view=2, older), img1 (view=5)
        # If view counts are equal, newer (created DESC) comes first
        self.assertEqual(len(ordered), 3)
        self.assertEqual(ordered[0].external_id, img2.external_id)
        self.assertEqual(ordered[1].external_id, img3.external_id)
        self.assertEqual(ordered[2].external_id, img1.external_id)

    def test_display_priority_deterministic_tiebreak(self):
        """Test that display_priority uses external_id for deterministic tie-breaking."""
        from django.utils import timezone

        now = timezone.now()

        # Create three images with identical view_count and created time
        images = []
        for i in range(3):
            img = self.image_service.create(
                {
                    "name": f"img{i}",
                    "file_path": "/test/",
                    "file_name": f"img{i}.jpg",
                }
            )
            img.view_count = 10
            img.created = now
            img.save()
            images.append(img)

        # Get ordered images
        ordered = list(self.image_service.get_ordered_images("display_priority"))

        # Should be ordered by external_id ascending (lexicographic)
        self.assertEqual(len(ordered), 3)
        ordered_ids = [img.external_id for img in ordered]
        self.assertEqual(ordered_ids, sorted(ordered_ids))

    def test_default_sort_backward_compat(self):
        """Test that omitting sort profile uses the existing -created default."""
        from datetime import timedelta
        from django.utils import timezone

        now = timezone.now()

        img1 = self.image_service.create(
            {
                "name": "oldest",
                "file_path": "/test/",
                "file_name": "oldest.jpg",
            }
        )
        img1.created = now - timedelta(hours=3)
        img1.save()

        img2 = self.image_service.create(
            {
                "name": "newest",
                "file_path": "/test/",
                "file_name": "newest.jpg",
            }
        )
        img2.created = now
        img2.save()

        # Get images with no sort profile (default)
        ordered = list(self.image_service.get_ordered_images(None))

        # Should be newest first (default -created order)
        self.assertEqual(ordered[0].external_id, img2.external_id)
        self.assertEqual(ordered[1].external_id, img1.external_id)

    def test_unknown_profile_raises(self):
        """Test that unknown sort profile raises ValueError."""
        self.image_service.create(self.full_image_data)

        with self.assertRaises(ValueError) as ctx:
            list(self.image_service.get_ordered_images("unknown_profile"))

        self.assertIn("unknown_profile", str(ctx.exception))
