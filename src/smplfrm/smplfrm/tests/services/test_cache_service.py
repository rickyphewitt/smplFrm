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
        display_type = "blur"
        height = "10"
        width = "20"

        self.assertEqual(
            f"{ext_id}:{display_type}:{height}:{width}",
            self.service.get_image_cache_key(ext_id, height, width),
        )

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="border")
    def test_image_cache_key_with_different_fill_mode(self):
        ext_id = "foo"
        height = "10"
        width = "20"

        cache_key = self.service.get_image_cache_key(ext_id, height, width)
        self.assertEqual(f"{ext_id}:border:{height}:{width}", cache_key)

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="zoom_to_fill")
    def test_image_cache_key_dynamically_uses_setting(self):
        ext_id = "bar"
        height = "100"
        width = "200"

        cache_key = self.service.get_image_cache_key(ext_id, height, width)
        self.assertEqual(f"{ext_id}:zoom_to_fill:{height}:{width}", cache_key)
