
from django.test import TestCase
from django.test.utils import override_settings

from smplfrm.services import CacheService


class TestImageService(TestCase):
    def setUp(self):
        self.service = CacheService()
        self.cache_key = "randomHere"
        self.cache_data = {
            "some": "data"
        }

    def test_create_get_invalidate_cache_item(self):

        self.service.upsert(self.cache_key, self.cache_data)
        self.assertEqual(self.service.read(self.cache_key), self.cache_data)
        self.service.delete(self.cache_key)
        self.assertIsNone(self.service.read(self.cache_key))

    @override_settings(SMPL_FRM_IMAGE_CACHE_TIMEOUT=1)
    def test_configurable_cache_timeout(self):
        self.service.upsert(self.cache_key, self.cache_data)
        from time import sleep
        sleep(2)
        self.assertIsNone(self.service.read(self.cache_key), self.cache_data)

    def test_clear_cache(self):
        self.service.upsert(self.cache_key, self.cache_data)
        self.service.clear()
        self.assertIsNone(self.service.read(self.cache_key), self.cache_data)



