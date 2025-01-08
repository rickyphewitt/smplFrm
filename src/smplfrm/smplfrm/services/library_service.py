
import logging
from django.conf import settings
import os

from smplfrm.settings import SMPL_FRM_IMAGE_FORMATS, BASE_DIR

logger = logging.getLogger(__name__)


class LibraryService(object):

# need to mark images not found in the scan as deleted in the DB, do not actually delete them
# should we also resurect them? I think so


    def __init__(self):
        from smplfrm.services import ImageService
        self.image_service = ImageService()


    def scan(self):
        logger.info(f"BASE DIR: {BASE_DIR}")
        current_dir = os.path.abspath(os.path.join(os.path.dirname( __file__ )))
        logger.info(f"{current_dir}")
        valid_image_ids = []
        for asset_dir in settings.SMPL_FRM_LIBRARY_DIRS:
            logger.info(f"Scanning dir: {asset_dir}")
            image_count = 0
            images_created = 0
            for dirpath, subdirs, filenames in os.walk(asset_dir):
                for filename in filenames:
                    try:
                        file_ext = filename.rsplit(".", 1)[1]
                    except IndexError:
                        logger.warning(f"Unable to parse file extension for file with name: {filename}")
                        continue
                    # load image files
                    if file_ext in SMPL_FRM_IMAGE_FORMATS:
                        file_path = os.path.join(dirpath, filename)
                        image_data = {
                            "name" : filename,
                            "file_path": file_path,
                            "file_name": filename
                        }
                        logger.info(f"Found image with filename: {filename} and path: {file_path}")
                        image_count = image_count + 1
                        # see if one exists with fpath and fname
                        existing_image = self.image_service.read_by_file_name_and_file_path(filename, file_path)
                        if existing_image:
                            if existing_image.deleted:
                                existing_image.deleted = False
                                existing_image.save()
                            valid_image_ids.append(existing_image.external_id)
                        else:
                            created_image = self.image_service.create(image_data)
                            images_created = images_created + 1
                            valid_image_ids.append(created_image.external_id)


            logger.info(f"found {image_count} image(s) and created {images_created} images(s)")
        # mark images as deleted if they didn't show up on the scan
        all_images = self.image_service.list().exclude(external_id__in=valid_image_ids)
        for image in all_images.iterator():
            image.deleted = True
            image.save()



    def load_images(self):
        """
        Reads images from disc and caches their locations
        to a file
        :return:
        """
        images_by_name = {}
        images_by_index = {}
        index = 0
        for asset_dir in settings.SMPL_FRM_LIBRARY_DIRS:
            for dirpath, subdirs, filenames in os.walk(asset_dir):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)

                    image_data = {filename: {"path": file_path}}
                    images_by_name.update(image_data)
                    images_by_index.update({index: image_data})

                    index = index + 1

        # write to cache
        self.cache.write(self.image_cache_by_name_key, images_by_name)
        self.cache.write(self.image_cache_by_index_key, images_by_index)
        # for now load the images into memory -> @TODO use an actual framework (DJANGO)!
        self.image_cache_by_name = images_by_name
        self.image_cache_cache_by_index = images_by_index

        print(f"Loaded {index} image(s)")