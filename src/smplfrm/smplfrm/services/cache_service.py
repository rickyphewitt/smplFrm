import logging
import string

from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)





class CacheService(object):

    def __init__(self):
        self.cache = cache





    def upsert(self, cache_key: string, cache_data: object, expires: int=None):
        """
        Update or insert an item for a given key
        :param cache_key:
        :param cache_data:
        :param expires:
        :return:
        """
        if expires is None:
            expires = settings.SMPL_FRM_IMAGE_CACHE_TIMEOUT
        self.cache.set(key=cache_key, value=cache_data, timeout=expires)

    def read(self, cache_key: string):
        return self.cache.get(cache_key)

    def delete(self, cache_key: string):
        self.cache.delete(cache_key)

    def clear(self, force=False):
        if settings.SMPL_FRM_CLEAR_CACHE_ON_BOOT is True or force:
            self.cache.clear()
            print("Cache Cleared")


    # cache keys
    def get_image_cache_key(self, external_id, height, width):
        return f"{external_id}:{height}:{width}"