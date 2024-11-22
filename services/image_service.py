import settings
import os
from random import Random
import cv2
import logging

from services.history_service import HistoryService

logger = logging.getLogger(__name__)



class ImageService(object):

    def __init__(self):
        self.image_cache = []
        self.image_cache_by_name = {}
        self.image_count = 0
        self.rand = Random()
        self.history = HistoryService()

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
                    self.image_cache_by_name.update({filename: file_path})

        self.image_cache = images
        self.image_count = len(self.image_cache)
        print(f"Loaded {self.image_count} image(s)")
        logger.info(f"Loaded {self.image_count} image(s)")
        return images

    def get_one(self, index=None):
        if index:
            return self.image_cache[index]

        image = self.rand.choice(seq=self.image_cache)

        try:
            self.history.add(image[0])
        except Exception:
            # continue to find an image that isn't in the history
            print(f"Image {image[0]} found in history, trying again.")
            image = self.get_one()

        print(f"Retuning image {image[0]}.")
        return image





    def scale(self, image: str, window_height, window_width):

        # sanitize the incoming image path and make sure its one we have
        image_name = image.rsplit("/", 1)[1]
        image_path = self.image_cache_by_name.get(image_name)
        if not image_name:
            #ToDo: more accurate exception here
            raise Exception()
        image_ext = image_path.rsplit(".", 1)[1]

        padding = 5
        # load image and get its w/h
        img = cv2.imread(image_path)
        # tuple of width / height
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        target_width = int(window_width) - padding
        target_height = int(window_height) - padding

        print(f"window_height: {window_height}, window_width: {window_width}")
        logger.info(f"window height: {window_height}")
        logger.info(f"window width: {window_width}")



        scale_height_size, scale_width_size = self.__determine_scaled_dimensions(target_width, target_height, image_w, image_h)
        vert_border, horz_border = self.__determine_boarder(scale_width_size, scale_height_size, target_width, target_height)

        print(f"target_height: {target_height}, target_width: {target_width}")
        resized_img = cv2.resize(img, (scale_width_size, scale_height_size), interpolation=cv2.INTER_AREA)
        resized_img = cv2.copyMakeBorder(resized_img, horz_border, horz_border, vert_border, vert_border, cv2.BORDER_REPLICATE, value=(0, 0, 0, 100)) #is opacity doing anything?



        _, enc_image = cv2.imencode(ext=f".{image_ext}", img=resized_img)
        return enc_image

    def __determine_scaled_dimensions(self, target_width, target_height, image_w, image_h):
        """
        Determine scaled values of image
        :param target_width:
        :param target_height:
        :param image_w:
        :param image_h:
        :return: scaled height, scaled width
        """

        # determine viewport orientation
        portrait_viewport = target_height > target_width

        # determine image orientation
        portrait_image = image_h > image_w

        scale_height_size = target_height
        scale_width_size = target_width

        if (portrait_viewport and portrait_image) or (not portrait_viewport and portrait_image):
            # scale by height
            scale_width_size = self.__scale_by(target_height, image_w, image_h)
        elif (portrait_viewport and not portrait_image) or (not portrait_viewport and not portrait_image):
            # scale by width
            scale_height_size = self.__scale_by(target_width, image_h, image_w)

        # check to see if either of the scaled sizes are larger than target
        if scale_height_size > target_height:
            scale_width_size = self.__scale_by(target_height, image_w, image_h)
            scale_height_size = target_height

        elif scale_width_size > target_width:
            scale_height_size = self.__scale_by(target_width, image_h, image_w)
            scale_width_size = target_width


        return scale_height_size, scale_width_size


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


    def __scale_by(self, scale_to, size_1, size_2):
        """
        Scale an image
        :param scale_to: size to scale image to
        :param size_1: w or h
        :param size_2: w or h
        :return:
        """
        return int(scale_to * size_1 / size_2)