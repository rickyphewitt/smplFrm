import unittest
from settings import ASSET_DIRECTORIES
from services.image_service import ImageService
from pathlib import Path
import cv2
class TestImageService(unittest.TestCase):


    def test_load_images(self):
        service = ImageService()
        images = service.load_images()

        self.assertEqual(len(images), 4, "Unexpected Image Count")

    def test_load_image(self):
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
        service = ImageService()
        service.load_images()

        window_h = 100
        window_w = 100
        padding = 5

        source_image = f"{ASSET_DIRECTORIES[0]}/sub_dir_assets/david-becker-F7SBonu15d8-unsplash.jpg"
        source_image_ext = source_image.rsplit(".", 1)[1]

        image = service.scale(source_image, window_height=window_h, window_width=window_w)

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
        service = ImageService()
        service.load_images()

        window_h = 100
        window_w = 100
        padding = 5

        source_image = f"{ASSET_DIRECTORIES[0]}/sub_dir_assets/kelly-sikkema-PqqQDpS6H6A-unsplash.jpg"
        source_image_ext = source_image.rsplit(".", 1)[1]

        image = service.scale(source_image, window_height=window_h, window_width=window_w)

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
        This test ensures that the image height matches when the scalee
        image height exceeds the height of the viewport
        :return:
        """
        service = ImageService()
        service.load_images()

        window_h = 100
        window_w = 1000
        padding = 5

        source_image = f"{ASSET_DIRECTORIES[0]}/sub_dir_assets/david-becker-F7SBonu15d8-unsplash.jpg"
        source_image_ext = source_image.rsplit(".", 1)[1]

        image = service.scale(source_image, window_height=window_h, window_width=window_w)

        # read raw image data and assert new values
        img = cv2.imdecode(image, -1)  # -1 means do not change image
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        self.assertEqual(window_w - 5, image_w)
        self.assertEqual(window_h - 5, image_h)
