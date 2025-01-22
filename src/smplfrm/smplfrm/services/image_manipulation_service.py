
import logging
import cv2
from PIL import Image as PIL_Image
from PIL.ExifTags import TAGS

from smplfrm.models import Image

logger = logging.getLogger(__name__)

class ImageManipulationService(object):

    def display(self, image, window_height=100, window_width=100):
        return self.__display_image(image, window_height, window_width)


    def __display_image(self, image, window_height, window_width):

        image_metadata = self.__extract_metadata(image.file_path)

        return self.__scale(image, window_height, window_width, image_meta=image_metadata)

    def __scale(self, image: Image, window_height, window_width, image_meta={}):

        # sanitize the incoming image path and make sure its one we have
        if image_meta is None:
            image_meta = {}
        image_ext = image.file_path.rsplit(".", 1)[1]

        padding = 0
        # load image and get its w/h
        img = cv2.imread(image.file_path)
        # tuple of width / height
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        # if target_width/height is 0 set it to the image_w/height
        if window_height == 0 or window_width == 0:
            window_height = image_h
            window_width = image_w

        target_width = int(window_width) - padding
        target_height = int(window_height) - padding

        logger.debug(f"window height: {window_height}")
        logger.debug(f"window width: {window_width}")

        scale_height_size, scale_width_size = self.__determine_scaled_dimensions(target_width, target_height, image_w, image_h)
        vert_border, horz_border = self.__determine_boarder(scale_width_size, scale_height_size, target_width, target_height)

        logger.debug(f"target_height: {target_height}")
        logger.debug(f"target_width: {target_width}")

        resized_img = cv2.resize(img, (scale_width_size, scale_height_size), interpolation=cv2.INTER_AREA)
        resized_img = cv2.copyMakeBorder(resized_img, horz_border, horz_border, vert_border, vert_border, cv2.BORDER_REPLICATE, value=(0, 0, 0, 100)) #is opacity doing anything?

        logger.info(f"Resized Image: {image.name}")
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


    def __extract_metadata(self, image_path):
        tag_dict = {}
        with PIL_Image.open(image_path) as img_pil:

            # Extract EXIF metadata using Pillow
            exif_data = img_pil.getexif()

            for k, v in exif_data.items():
                tag_dict[TAGS.get(k, k)] = v

        return tag_dict