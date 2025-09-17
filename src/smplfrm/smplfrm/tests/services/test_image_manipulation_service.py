from django.test import TestCase

from smplfrm.services import ImageService
from smplfrm.services import LibraryService

import cv2

from smplfrm.services.image_manipulation_service import ImageManipulationService


class TestImageService(TestCase):
    def setUp(self):
        self.image_service = ImageService()
        self.image_manipulation_service = ImageManipulationService()
        self.padding = 0
        # bootstrap the images
        LibraryService().scan()

    def test_display_image(self):

        image = self.image_service.list()[0]

        displayed_image = self.image_manipulation_service.display(image, 100, 100)
        self.assertIsNotNone(displayed_image, "Displayed Image should not be None!")

    def test_scale_horizontal_image(self):
        """
        Test scaling an image to keep aspect ratio
        :return:
        """

        window_h = 100
        window_w = 100

        image = self.image_service.list(
            file_name="david-becker-F7SBonu15d8-unsplash.jpg"
        )[0]

        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        # read raw image data and assert new values
        img = cv2.imdecode(displayed_image, -1)  # -1 means do not change image
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        self.assertEqual(window_w - self.padding, image_w)
        self.assertEqual(window_h - self.padding, image_h)  # for rounding

    def test_scale_vertical_image(self):
        """
        Test scaling an image to keep aspect ratio
        :return:
        """

        window_h = 100
        window_w = 100

        image = self.image_service.list(
            file_name="kelly-sikkema-PqqQDpS6H6A-unsplash.jpg"
        )[0]

        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        # read raw image data and assert new values
        img = cv2.imdecode(displayed_image, -1)  # -1 means do not change image
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        self.assertEqual(window_h - self.padding, image_h)
        # assert that the width has been filled as well
        self.assertEqual(window_w - self.padding, image_w)
        self.assertEqual(window_h - self.padding, image_h)

    def test_scale_horizontal_image_height_larger_than_viewport(self):
        """
        This test ensures that the image height matches when the scale
        image height exceeds the height of the viewport
        :return:
        """
        window_h = 100
        window_w = 1000

        image = self.image_service.list(
            file_name="kelly-sikkema-PqqQDpS6H6A-unsplash.jpg"
        )[0]

        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        # read raw image data and assert new values
        img = cv2.imdecode(displayed_image, -1)  # -1 means do not change image
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        self.assertEqual(window_w - self.padding, image_w)
        self.assertEqual(window_h - self.padding, image_h)

    def test_scale_panoramic_image(self):

        window_h = 433
        window_w = 952

        image = self.image_service.list(
            file_name="bernd-dittrich-73scJ3UOdHM-unsplash.jpg"
        )[0]

        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        # read raw image data and assert new values
        img = cv2.imdecode(displayed_image, -1)  # -1 means do not change image
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        self.assertEqual(window_w - self.padding, image_w)
        self.assertEqual(window_h - self.padding, image_h)  # rounding

    def _assert_image(self, image, name="name"):
        self.assertIsNotNone(image.external_id, "External Id should be set on Create.")
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
