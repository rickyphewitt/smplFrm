from django.test import TestCase
from django.test.utils import override_settings

from smplfrm.services import CacheService


class TestImageService(TestCase):
    def setUp(self):
        self.service = CacheService()
        self.cache_key = "randomHere"
        self.cache_data = {"some": "data"}

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

    def test_clear_cache_forced(self):
        self.service.upsert(self.cache_key, self.cache_data)
        self.service.clear(force=True)
        self.assertIsNone(self.service.read(self.cache_key), self.cache_data)

    def test_clear_cache_protected(self):
        """
        Neither SMPL_FRM_CLEAR_CACHE_ON_BOOT or force
        is set to true so cache is not cleared
        :return:
        """
        self.service.upsert(self.cache_key, self.cache_data)
        self.service.clear()
        self.assertIsNotNone(self.service.read(self.cache_key), self.cache_data)

    @override_settings(SMPL_FRM_CLEAR_CACHE_ON_BOOT=True)
    def test_clear_cache_env_var(self):
        self.service.upsert(self.cache_key, self.cache_data)
        self.service.clear(force=True)
        self.assertIsNone(self.service.read(self.cache_key), self.cache_data)

    def test_image_cache_key(self):
        ext_id = "foo"
        height = "10"
        width = "20"

        self.assertEqual(
            f"{ext_id}:{height}:{width}",
            self.service.get_image_cache_key(ext_id, height, width),
        )
