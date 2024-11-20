import settings
import os
from random import Random
import cv2
import logging

logger = logging.getLogger(__name__)



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
        print(settings.ASSET_DIRECTORIES)
        for asset_dir in settings.ASSET_DIRECTORIES:
            for dirpath, subdirs, filenames in os.walk(asset_dir):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    images.append((filename, file_path))

        self.image_cache = images
        self.image_count = len(self.image_cache)
        print(f"Loaded {self.image_count} image(s)")
        logger.info(f"Loaded {self.image_count} image(s)")
        return images

    def get_one(self, index=None):
        if index:
            return self.image_cache[index]
        return self.rand.choice(seq=self.image_cache)

    def scale(self, image: str, window_height, window_width):
        padding = 5
        # load image and get its w/h
        img = cv2.imread(image)
        # tuple of width / height
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        target_width = int(window_width) - padding
        target_height = int(window_height) - padding

        scale_width = int(window_width) - padding
        scale_height = int(window_height) - padding
        print(f"window_height: {window_height}, window_width: {window_width}")
        logger.info(f"window height: {window_height}")
        logger.info(f"window width: {window_width}")
        image_ext = image.rsplit(".", 1)[1]

        scale_width_size = scale_width
        scale_height_size = scale_height
        if target_height > target_width:
            # scale based on target width to get correct height
            scale_height_size = int(scale_width * image_h / image_w)
        elif target_width > target_height:
            # scale based on target height to get correct width
            scale_width_size = int(scale_height * image_w / image_h)
        else:
            # target height/width is the same, scale based on the largest image dimension
            if image_h > image_w:
                # scale based on height to get correct width
                scale_width_size = int(scale_height * image_w / image_h)
            else:
                # if they are the same or width is greater scale to get correct height
                scale_height_size = int(scale_width * image_h / image_w)


        vert_border, horz_border = self.__determine_boarder(scale_width_size, scale_height_size, target_width, target_height)

        print(f"scale_height: {scale_height}, scale_width: {scale_width}")
        resized_img = cv2.resize(img, (scale_width_size, scale_height_size), interpolation=cv2.INTER_AREA)
        resized_img = cv2.copyMakeBorder(resized_img, horz_border, horz_border, vert_border, vert_border, cv2.BORDER_REPLICATE, value=(0, 0, 0, 100)) #is opacity doing anything?



        _, enc_image = cv2.imencode(ext=f".{image_ext}", img=resized_img)
        return enc_image


    def __determine_boarder(self, scale_width, scale_height, target_width, target_height):
        """
        Determines the boarder
        :param scale_width:
        :param scale_height:
        :param target_width:
        :param target_height:
        :return:
        """
        vertical_border = 0
        horizontal_border = 0
        if scale_width < target_width:
            vertical_border = target_width - scale_width
            vertical_border = int(vertical_border/2)

        if scale_height < target_height:
            horizontal_border = target_height - scale_height
            horizontal_border = int(horizontal_border/2)

        return vertical_border, horizontal_border
