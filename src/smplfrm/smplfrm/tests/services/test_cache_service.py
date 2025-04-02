
from django.test import TestCase

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





