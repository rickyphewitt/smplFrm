from django.test import TestCase
from django.db.models import ObjectDoesNotExist

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

    def test_reset_all_view_count_reports_progress(self):
        """Test that reset_all_view_count calls on_progress per image."""
        self.image_service.create(self.full_image_data)
        self.image_service.create(
            {"name": "bar", "file_path": "/other/", "file_name": "bar.jpg"}
        )

        progress_values = []
        self.image_service.reset_all_view_count(
            on_progress=lambda pct: progress_values.append(pct)
        )

        self.assertEqual(len(progress_values), 2)
        self.assertEqual(progress_values[0], 50)
        self.assertEqual(progress_values[1], 100)

    def test_reset_all_view_count_works_without_callback(self):
        """Test that reset_all_view_count works when on_progress is None."""
        image = self.image_service.create(self.full_image_data)
        self.image_service.increment_view_count(image)

        self.image_service.reset_all_view_count()

        image.refresh_from_db()
        self.assertEqual(image.view_count, 0)
