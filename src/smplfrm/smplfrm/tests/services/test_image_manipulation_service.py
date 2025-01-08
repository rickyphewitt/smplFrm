
from django.test import TestCase

from smplfrm.services import ImageService
from smplfrm.services import LibraryService
from django.db.models import ObjectDoesNotExist

from smplfrm.services.image_manipulation_service import ImageManipulationService


class TestImageService(TestCase):
    def setUp(self):
        self.image_service = ImageService()
        self.image_manipulation_service = ImageManipulationService()
        # bootstrap the images
        LibraryService().scan()



    def test_display_image(self):

        image = self.image_service.list()[0]

        displayed_image = self.image_manipulation_service.display(image, 100, 100)
        self.assertIsNotNone(displayed_image, "Displayed Image should not be None!")

    def _assert_image(self, image, name="name"):
        self.assertIsNotNone(image.external_id, "External Id should be set on Create.")
        self.assertIsNotNone(image.external_id, "External Id should be set on Create.")
        self.assertIsNotNone(image.created, "Created Datetime not set.")
        self.assertIsNotNone(image.updated, "Updated Datetime not set.")
        self.assertEqual(image.name, self.full_image_data[name], "Name not set.")
        self.assertEqual(image.file_path, self.full_image_data["file_path"], "File_path not set.")
        self.assertEqual(image.file_name, self.full_image_data["file_name"], "File_name not set.")
