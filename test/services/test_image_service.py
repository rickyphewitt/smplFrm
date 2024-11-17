import unittest
from services.image_service import ImageService
from pathlib import Path
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
