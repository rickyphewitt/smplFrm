import logging
import string
from typing import Dict

from smplfrm.models import Image

logger = logging.getLogger(__name__)


class ImageService(object):


    def create(self, data: Dict):
        return Image.objects.create(**data)

    def read(self, ext_id: string, deleted: bool=False):
        return Image.objects.get(external_id = ext_id, deleted=deleted)


    def list(self, **kwargs):

        if kwargs:
            return Image.objects.filter(**kwargs)
        else:
            return Image.objects.all()

    def update(self, image: Image):
        image.save()
        return image


    def delete(self, ext_id: string):

        image_to_soft_delete = None

        try:
            image_to_soft_delete = Image.objects.get(external_id = ext_id, deleted=False)
        except Image.DoesNotExist:
            return

        image_to_soft_delete.deleted = True
        image_to_soft_delete.save()


    def destroy(self, ext_id: string):
        """
        Permanently delete an image from the database
        :param ext_id:
        :return:
        """

        image_to_destroy = None

        try:
            image_to_destroy = Image.objects.get(external_id = ext_id)
        except Image.DoesNotExist:
            return

        image_to_destroy.delete()


    ## non base service methods
    def read_by_file_name_and_file_path(self, file_name: str, file_path:str):
        try:
            return Image.objects.get(file_name=file_name, file_path=file_path)
        except Image.DoesNotExist:
            return None


    def get_next(self):
        """
        Returns the least viewed image that was created most recently
        :return:
        """

        try:
            images = Image.objects.all().filter(deleted=False).order_by("view_count", "-created")[:1]
            image = images[0]
            image.view_count = image.view_count + 1
            image.save()
            return image
        except Exception as e:
            logger.error(f"Failed to load next image: {str(e)}")

        return None

