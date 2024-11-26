import unittest
from unittest import SkipTest

from settings import LIBRARY_DIRECTORIES, Settings
from services.image_service import ImageService
from services.history_service import HistoryService
from pathlib import Path
import cv2
from unittest.mock import patch, Mock
class TestImageService(unittest.TestCase):


    def test_load_images(self):
        service = ImageService()
        images = service.load_images()

        self.assertEqual(len(images), 5, "Unexpected Image Count")

    def test_load_image(self):
        HistoryService().clean()
        service = ImageService()
        service.load_images()
        image = service.get_one()
        self.assertIsNotNone(image, "Image tuple is None")
        self.assertIsNotNone(image[0], "Name of image not found")
        self.assertIsNotNone(image[1], "File Path of image not found")
        self.assertTrue(Path(image[1]).exists(), "File not found")


    def test_scale_horizontal_image(self):
        """
        Test scaling an image to keep aspect ratio
        :return:
        """
        HistoryService().clean()
        service = ImageService()
        service.load_images()

        window_h = 100
        window_w = 100
        padding = 5

        source_image = f"{LIBRARY_DIRECTORIES[0]}/sub_dir_assets/david-becker-F7SBonu15d8-unsplash.jpg"
        source_image_ext = source_image.rsplit(".", 1)[1]

        image = service.display_image(source_image, window_height=window_h, window_width=window_w)

        # read raw image data and assert new values
        img = cv2.imdecode(image, -1) # -1 means do not change image
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        self.assertEqual(window_w-5, image_w)
        self.assertEqual(window_h-6, image_h) # for rounding


    def test_scale_vertical_image(self):
        """
        Test scaling an image to keep aspect ratio
        :return:
        """
        HistoryService().clean()
        service = ImageService()
        service.load_images()

        window_h = 100
        window_w = 100
        padding = 5

        source_image = f"{LIBRARY_DIRECTORIES[0]}/sub_dir_assets/kelly-sikkema-PqqQDpS6H6A-unsplash.jpg"
        source_image_ext = source_image.rsplit(".", 1)[1]

        image = service.display_image(source_image, window_height=window_h, window_width=window_w)

        # read raw image data and assert new values
        img = cv2.imdecode(image, -1) # -1 means do not change image
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        self.assertEqual(window_h-padding, image_h)
        # assert that the width has been filled as well
        self.assertEqual(window_w - padding, image_w)
        self.assertEqual(window_h - padding, image_h)


    def test_scale_horizontal_image_height_larger_than_viewport(self):
        """
        This test ensures that the image height matches when the scale
        image height exceeds the height of the viewport
        :return:
        """
        service = ImageService()
        service.load_images()

        window_h = 100
        window_w = 1000
        padding = 5

        source_image = f"{LIBRARY_DIRECTORIES[0]}/sub_dir_assets/david-becker-F7SBonu15d8-unsplash.jpg"
        source_image_ext = source_image.rsplit(".", 1)[1]

        image = service.display_image(source_image, window_height=window_h, window_width=window_w)

        # read raw image data and assert new values
        img = cv2.imdecode(image, -1)  # -1 means do not change image
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        self.assertEqual(window_w - 5, image_w)
        self.assertEqual(window_h - 5, image_h)

    def test_scale_panoramic_image(self):
        HistoryService().clean()
        service = ImageService()
        service.load_images()

        window_h = 433
        window_w = 952
        padding = 5

        source_image = f"{LIBRARY_DIRECTORIES[0]}/2024/11/bernd-dittrich-73scJ3UOdHM-unsplash.jpg"
        source_image_ext = source_image.rsplit(".", 1)[1]

        image = service.display_image(source_image, window_height=window_h, window_width=window_w)

        # read raw image data and assert new values
        img = cv2.imdecode(image, -1)  # -1 means do not change image
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        self.assertEqual(window_w - 5, image_w)
        self.assertEqual(window_h - 6, image_h)


    @patch("services.image_service.HistoryService")
    def test_do_not_repeat_last_image(self, mock_history):

        def side_effect(*args, **kwargs):
            if mock_history.add.call_count == 1:
                raise Exception()

        mock_history.add = Mock(side_effect=side_effect)

        service = ImageService()
        service.load_images()
        setattr(service, "history", mock_history)
        service.get_one()

        self.assertEqual(mock_history.add.call_count, 2)

    def test_image_not_found(self):
        service = ImageService()
        service.load_images()
        self.assertRaises(Exception, service.display_image, "/no/image/here/foo.png", 5, 5)


    def test_datetime_parsing(self):
        service = ImageService()

        parsable_dates = [
            ("2014:10:18 13:49:12","October, 2014"),
            ("2014:07:25 19:39:59.283", "July, 2014"),
            ("2014:03:19 18:15:53+00:00", "March, 2014"),
            ("UnparsableDate", "UnparsableDate")
        ]

        for date, expected_date in parsable_dates:
            metadata = {'DateTime': date}
            datetime = service.parse_date(metadata)
            self.assertEqual(expected_date, datetime)
