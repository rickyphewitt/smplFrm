import abc
import logging
import string
from typing import Dict

logger = logging.getLogger(__name__)

class BaseService(abc.ABC):

    def create(self, data: Dict):
        pass

    def read(self, ext_id: string, deleted: bool=False):
        pass

    def list(self, **kwargs):
        pass
    def update(self, object):
        pass
    def delete(self, ext_id: string):
        pass

    def destroy(self, ext_id: string):
        pass