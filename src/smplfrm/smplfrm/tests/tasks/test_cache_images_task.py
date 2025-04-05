import os
from django.test import TestCase

from smplfrm.services import ImageService, LibraryService, CacheService
from smplfrm.tasks import cache_images
from django.test.utils import override_settings

test_library = [os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', 'library'))]


@override_settings(SMPL_FRM_LIBRARY_DIRS=test_library)
class TestCacheImagesTask(TestCase):

    def setUp(self):
        super().setUpClass()
        self.cache_service = CacheService()
        self.image_service = ImageService()
        self.library_service = LibraryService()
        self.library_service.scan()
        self.images = images = self.image_service.list()[:5]
        self.image_ext_ids = []
        for image in images:
            self.image_ext_ids.append(image.external_id)


    def test_cache_images(self):
        self.cache_service.clear(force=True)
        height = "10"
        width = "20"

        # verify they are not cached
        for ext_id in self.image_ext_ids:
            cache_key = self.cache_service.get_image_cache_key(ext_id, height, width)
            cached_image = self.cache_service.read(cache_key=cache_key)
            self.assertIsNone(cached_image)

        # feed them to the task
        cache_images(self.image_ext_ids, height, width)
        # verify they are cached
        for ext_id in self.image_ext_ids:
            cache_key = self.cache_service.get_image_cache_key(ext_id, height, width)
            cached_image = self.cache_service.read(cache_key=cache_key)
            self.assertIsNotNone(cached_image)

    def test_cache_no_images(self):
        self.cache_service.clear(force=True)
        # grab a list of images
        height = "10"
        width = "20"

        # verify they are not cached
        for ext_id in self.image_ext_ids:
            cache_key = self.cache_service.get_image_cache_key(ext_id, height, width)
            cached_image = self.cache_service.read(cache_key=cache_key)
            self.assertIsNone(cached_image)

        # feed them to the task with various args being None
        cache_images([], height, width)
        cache_images(None, height, width)
        cache_images(self.image_ext_ids, None, width)
        cache_images(self.image_ext_ids, height, None)

        # verify they are not cached
        for ext_id in self.image_ext_ids:
            cache_key = self.cache_service.get_image_cache_key(ext_id, height, width)
            cached_image = self.cache_service.read(cache_key=cache_key)
            self.assertIsNone(cached_image)