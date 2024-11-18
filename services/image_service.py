import settings
import os
from random import Random
import cv2

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

    def get_one(self, index=None):
        if index:
            return self.image_cache[index]
        return self.rand.choice(seq=self.image_cache)

    def  scale(self, image: str, window_height, window_width):
        padding = 5
        # load image and get its w/h
        img = cv2.imread(image)
        # tuple of width / height
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]
        scale_width_size = int(window_width) - padding
        scale_height_size = int(window_height) - padding
        aspect_ratio = image_w / image_h
        image_ext = image.rsplit(".", 1)[1]

        if image_h > image_w:
            # scale vert
            scale_width_size = int(scale_height_size / aspect_ratio)
        else:
            # scale horiz
            scale_height_size = int(scale_width_size / aspect_ratio)

        resized_img = cv2.resize(img, (scale_width_size, scale_height_size), interpolation=cv2.INTER_AREA)

        _, enc_image = cv2.imencode(ext=f".{image_ext}", img=resized_img)
        return enc_image

        # if image_w > scale_width_size:
        #     # scale
        #     scale_height_size = int(scale_width_size / aspect_ratio)
        #     resized_img = cv2.resize(img, (scale_width_size, scale_height_size), interpolation=cv2.INTER_AREA)
        #
        #     _, enc_image = cv2.imencode(ext=f".{image_ext}", img=resized_img)
        #     return enc_image




    def calculate_scale(self, image, image_height, image_width, window_height, window_width):
        padding = 5

        # for now assume the screen is landscape
        # @ToDo handle portrait screens

        scale_width_size = window_width - padding


