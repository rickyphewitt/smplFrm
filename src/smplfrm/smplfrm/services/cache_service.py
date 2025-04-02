import logging
import string
from datetime import datetime

from django.core.cache import cache

logger = logging.getLogger(__name__)


class CacheService(object):

    def __init__(self):
        self.cache = cache





    def upsert(self, cache_key: string, cache_data: object, expires=86400):
        """
        Update or insert an item for a given key
        :param cache_key:
        :param cache_data:
        :param expires:
        :return:
        """
        self.cache.set(key=cache_key, value=cache_data, timeout=expires)

    def read(self, cache_key: string):
        return self.cache.get(cache_key)

    def delete(self, cache_key: string):
        self.cache.delete(cache_key)