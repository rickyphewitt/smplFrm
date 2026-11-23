from unittest.mock import patch

from django.test import TestCase
from PIL import Image as PIL_Image

from smplfrm.services import CacheService
from smplfrm.tasks import cache_images
from smplfrm.tests.library_filter_fixtures import (
    activate_filter,
    make_image,
    set_filtering,
)


@patch(
    "smplfrm.services.image_manipulation_service.ImageManipulationService.display",
    side_effect=lambda image, height, width: PIL_Image.new("RGB", (width, height)),
)
class TestCacheImagesVisibility(TestCase):
    def setUp(self):
        self.cache_service = CacheService()
        self.cache_service.clear()
        self.addCleanup(self.cache_service.clear)
        self.framed = make_image("framed.jpg", tags=["frame"])
        self.plain = make_image("plain.jpg")
        set_filtering(True)
        activate_filter("frame")

    def cached(self, image):
        key = self.cache_service.get_image_cache_key(image.external_id, "10", "20")
        return self.cache_service.read(cache_key=key) is not None

    def test_only_visible_images_are_cached(self, display):
        with self.assertLogs("smplfrm.tasks.tasks", "DEBUG") as logs:
            cache_images([self.framed.external_id, self.plain.external_id], "10", "20")

        self.assertTrue(self.cached(self.framed))
        self.assertFalse(self.cached(self.plain))
        self.assertEqual(display.call_count, 1)
        self.assertTrue(
            any(self.plain.external_id in line for line in logs.output),
            "The hidden id should be logged at DEBUG",
        )

    def test_deleted_images_are_not_cached(self, display):
        set_filtering(False)
        deleted = make_image("gone.jpg", deleted=True)

        cache_images([deleted.external_id], "10", "20")

        self.assertFalse(self.cached(deleted))
        display.assert_not_called()
