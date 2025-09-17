import logging
import os

from PIL import Image as PIL_Image
from PIL import TiffImagePlugin
from PIL.ExifTags import TAGS
from django.conf import settings
from smplfrm.settings import SMPL_FRM_IMAGE_FORMATS, BASE_DIR

logger = logging.getLogger(__name__)


class LibraryService(object):

    # need to mark images not found in the scan as deleted in the DB, do not actually delete them
    # should we also resurect them? I think so

    def __init__(self):
        from smplfrm.services import ImageMetadataService
        from smplfrm.services import ImageService

        self.image_service = ImageService()
        self.image_metadata_service = ImageMetadataService()

    def scan(self):
        logger.info(f"BASE DIR: {BASE_DIR}")
        current_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
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
                        logger.warning(
                            f"Unable to parse file extension for file with name: {filename}"
                        )
                        continue
                    # load image files
                    if file_ext in SMPL_FRM_IMAGE_FORMATS:
                        file_path = os.path.join(dirpath, filename)
                        image_data = {
                            "name": filename,
                            "file_path": file_path,
                            "file_name": filename,
                        }
                        logger.info(
                            f"Found image with filename: {filename} and path: {file_path}"
                        )
                        image_count = image_count + 1
                        # see if one exists with fpath and fname
                        existing_image = (
                            self.image_service.read_by_file_name_and_file_path(
                                filename, file_path
                            )
                        )
                        if existing_image:
                            if existing_image.deleted:
                                existing_image.deleted = False
                                existing_image.save()
                            self.save_image_meta(existing_image)
                            valid_image_ids.append(existing_image.external_id)
                        else:
                            created_image = self.image_service.create(image_data)
                            images_created = images_created + 1
                            valid_image_ids.append(created_image.external_id)
                            self.save_image_meta(created_image)

            logger.info(
                f"found {image_count} image(s) and created {images_created} images(s)"
            )
        # mark images as deleted if they didn't show up on the scan
        all_images = self.image_service.list().exclude(external_id__in=valid_image_ids)
        for image in all_images.iterator():
            image.deleted = True
            image.save()

    def save_image_meta(self, image):
        tag_dict = self.__extract_metadata(image.file_path)
        image_meta = {
            "image": image,
            "exif": tag_dict,
        }

        existing_meta = None
        try:
            existing_meta = image.meta
            existing_meta.exif = image_meta["exif"]
            self.image_metadata_service.update(existing_meta)
        except Exception as e:
            self.image_metadata_service.create(image_meta)

    def __extract_metadata(self, image_path):
        tag_dict = {}
        with PIL_Image.open(image_path) as img_pil:

            # Extract EXIF metadata using Pillow
            exif_data = img_pil.getexif()

            for k, v in exif_data.items():
                try:
                    tag_dict[TAGS.get(k, k)] = self.__cast_to_json_compatible(v)
                except Exception as e:
                    logger.warning(
                        f"Failed to parse all metadata for image: {image_path}, error: {str(e)}"
                    )
        return tag_dict

    def __cast_to_json_compatible(self, value):
        if isinstance(value, TiffImagePlugin.IFDRational):
            return float(value)
        elif isinstance(value, tuple):
            return tuple(self.__cast_to_json_compatible(t) for t in value)
        elif isinstance(value, bytes):
            return value.decode(errors="replace")
        elif isinstance(value, dict):
            for k, v in value.items():
                value[k] = self.__cast_to_json_compatible(v)
            return value
        else:
            return value
