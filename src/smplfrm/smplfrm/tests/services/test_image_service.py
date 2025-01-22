
from django.test import TestCase

from smplfrm.services import ImageService
from django.db.models import ObjectDoesNotExist


class TestImageService(TestCase):
    def setUp(self):
        self.image_service = ImageService()
        self.full_image_data = {
            "name": "foo",
            "file_path": "./nested/file/",
            "file_name": "image.jpg"
        }

    def test_create_get_delete_image(self):

        created_image = self.image_service.create(self.full_image_data)
        self._assert_image(created_image)

        # get image from db by external id
        getted_image = self.image_service.read(ext_id=created_image.external_id)
        self._assert_image(created_image)
        self.assertEqual(created_image.external_id, getted_image.external_id, "External Ids should match!")

        # update image
        getted_image.name = "bar"
        updated_image = self.image_service.update(getted_image)
        self.assertEqual(updated_image.name, getted_image.name, "Name not set.")
        self.assertFalse(updated_image.deleted, "Image should not be deleted")

        # soft delete image
        self.image_service.delete(updated_image.external_id)
        # assert you can't read the image by default
        self.assertRaises(ObjectDoesNotExist, self.image_service.read, updated_image.external_id)
        # assert you can still pull the image when looking for deleted objects
        soft_deleted_image = self.image_service.read(updated_image.external_id, deleted=True)
        self.assertEqual(soft_deleted_image.name, soft_deleted_image.name, "Name not set.")
        self.assertTrue(soft_deleted_image.deleted, "Image should be deleted")

    def test_next(self):
        created_image = self.image_service.create(self.full_image_data)
        self._assert_image(created_image)
        getted_image = self.image_service.read(ext_id=created_image.external_id)

        view_count_before_next = getted_image.view_count
        image = self.image_service.get_next()

        getted_image = self.image_service.read(ext_id=created_image.external_id)
        self.assertEqual(view_count_before_next + 1, getted_image.view_count)

        # create second image and ensure its called 'next'
        second_image_data = {
            "name": "second-foo",
            "file_path": "/second/image/file/",
            "file_name": "second_image.jpg"
        }
        second_image = self.image_service.create(second_image_data)
        image = self.image_service.get_next()

        self.assertEqual(second_image.external_id, image.external_id)



    def _assert_image(self, image, name="name"):
        self.assertIsNotNone(image.external_id, "External Id should be set on Create.")
        self.assertIsNotNone(image.external_id, "External Id should be set on Create.")
        self.assertIsNotNone(image.created, "Created Datetime not set.")
        self.assertIsNotNone(image.updated, "Updated Datetime not set.")
        self.assertEqual(image.name, self.full_image_data[name], "Name not set.")
        self.assertEqual(image.file_path, self.full_image_data["file_path"], "File_path not set.")
        self.assertEqual(image.file_name, self.full_image_data["file_name"], "File_name not set.")
