import logging
import string
from typing import List, Dict
from datetime import datetime, timedelta

import cv2
from PIL import Image as PIL_Image
from PIL.ExifTags import TAGS

from smplfrm.settings import SMPL_FRM_DISPLAY_DATE, SMPL_FRM_FORCE_DATE_FROM_PATH
from smplfrm.models import ImageMetadata

from .base_service import BaseService

logger = logging.getLogger(__name__)

class ImageMetadataService(BaseService):


    def create(self, data: Dict):
        date = self.extract_date(data["image"].file_path, data["exif"])
        data["taken"] = date
        return ImageMetadata.objects.create(**data)

    def read(self, ext_id: string, deleted: bool=False):
        return ImageMetadata.objects.get(external_id = ext_id, deleted=deleted)


    def list(self, **kwargs):

        if kwargs:
            return ImageMetadata.objects.filter(**kwargs)
        else:
            return ImageMetadata.objects.all()

        pass
    def update(self, image_meta: ImageMetadata):
        date = self.extract_date(image_meta.image.file_path, image_meta.exif)
        image_meta.taken = date
        image_meta.save()
        return image_meta


    def delete(self, ext_id: string):

        image_meta_to_soft_delete = None

        try:
            image_meta_to_soft_delete = ImageMetadata.objects.get(external_id = ext_id, deleted=False)
        except ImageMetadata.DoesNotExist:
            return

        image_meta_to_soft_delete.deleted = True
        image_meta_to_soft_delete.save()


    def destroy(self, ext_id: string):
        """
        Permanently delete an image from the database
        :param ext_id:
        :return:
        """

        image_meta_to_destroy = None

        try:
            image_meta_to_destroy = ImageMetadata.objects.get(external_id = ext_id)
        except ImageMetadata.DoesNotExist:
            return

        image_meta_to_destroy.delete()

    ## non base service methods

    def read_by_image_id(self, image_ext_id):
        return ImageMetadata.objects.get(image__external_id=image_ext_id)




    def extract_date(self, image_path, image_meta):
        date_str = ""
        if SMPL_FRM_FORCE_DATE_FROM_PATH:
            date_str = self.parse_date_from_path(image_path)
            logger.info(f"Found Date String {date_str} from path.")
        elif "DateTime" not in image_meta:
            logger.error(f"Unable to Find DateTime in image meta: {image_meta}, defaulting to image name.")
            image_meta.update({"DateTime": "Unknown"})
            date_str = self.parse_date_from_meta(image_meta)

        return date_str


    def parse_date_from_meta(self, image_meta):
        """
        Parse date if possible
        :param image_meta:
        :return:
        """

        manual_dt_parsing = [
            "%Y:%m:%d %H:%M:%S",    # '2014:10:18 13:49:12'
            "%Y:%m:%d %H:%M:%S.%f", # '2014:07:25 19:39:59.283'
            "%Y:%m:%d %H:%M:%S%z"   # '2014:03:19 18:15:53+00:00'
        ]

        string_date = image_meta["DateTime"]
        parsed_date = None

        for dt_format in manual_dt_parsing:
            try:
                return datetime.strptime(string_date, dt_format)
            except Exception as e:
                print(f"Failed to extract DateTime from meta {string_date}, error: {str(e)}")
                pass

        if parsed_date is None:
            return string_date


    def parse_date_from_path(self, path):
        import re

        match = re.search("([12]\d{3}/(0[1-9]|1[0-2]))", path)
        parsed_date = None
        if match:
            # split on remainng /
            parts = match.group(0)
            parsed_date = datetime.strptime(match.group(0), "%Y/%m")
            # for now put the images further from day 1 of the month for tz issues
            # @ToDo handle this a better way?
            parsed_date = parsed_date + timedelta(days=1, seconds=1, microseconds=999)
        return parsed_date