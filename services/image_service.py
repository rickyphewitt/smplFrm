import settings
import os
from random import Random
class ImageService(object):

    def __init__(self):
        self.image_cache = []
        self.image_count = 0
        self.rand = Random()

    def load_images(self, reload=False):
        if not reload and len(self.image_cache) > 0:
            return self.image_cache
        # load images
        images = []
        for asset_dir in settings.ASSET_DIRECTORIES:
            for dirpath, subdirs, filenames in os.walk(asset_dir):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    images.append((filename, file_path))

        self.image_cache = images
        self.image_count = len(self.image_cache)
        return images

    def get_one(self):
        return self.rand.choice(seq=self.image_cache)




