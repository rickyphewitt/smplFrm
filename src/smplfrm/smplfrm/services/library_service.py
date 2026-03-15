import logging
import os
from typing import Any, Dict, List

from PIL import Image as PIL_Image
from PIL import TiffImagePlugin
from PIL.ExifTags import TAGS
from django.conf import settings

from smplfrm.settings import SMPL_FRM_IMAGE_FORMATS, BASE_DIR
from smplfrm.services.task_reporting_service import TaskReportingService
from smplfrm.models.task import TaskType

logger = logging.getLogger(__name__)


class LibraryService(TaskReportingService):
    """Service for scanning and managing image library."""

    def __init__(self) -> None:
        from smplfrm.services import ImageMetadataService, ImageService

        super().__init__(task_type=TaskType.RESCAN_LIBRARY)
        self.image_service = ImageService()
        self.image_metadata_service = ImageMetadataService()

    def scan(self, task_id=None) -> None:
        """Scan configured library directories for images and update database."""

        logger.info(f"BASE DIR: {BASE_DIR}")
        current_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
        logger.info(f"{current_dir}")
        valid_image_ids: List[str] = []

        # Count total files first for progress reporting
        total_files = 0
        for asset_dir in settings.SMPL_FRM_LIBRARY_DIRS:
            for dirpath, subdirs, filenames in os.walk(asset_dir):
                for filename in filenames:
                    file_ext = self._get_file_extension(filename)
                    if file_ext and file_ext in SMPL_FRM_IMAGE_FORMATS:
                        total_files += 1

        # start task
        self.initiate_task(task_id, total_files)

        try:
            processed = 0
            for asset_dir in settings.SMPL_FRM_LIBRARY_DIRS:
                logger.info(f"Scanning dir: {asset_dir}")
                image_count = 0
                images_created = 0

                for dirpath, subdirs, filenames in os.walk(asset_dir):
                    for filename in filenames:
                        file_ext = self._get_file_extension(filename)
                        if not file_ext:
                            continue

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
                            image_count += 1

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
                                images_created += 1
                                valid_image_ids.append(created_image.external_id)
                                self.save_image_meta(created_image)

                            processed += 1
                            self.report_task(processed)

                logger.info(
                    f"found {image_count} image(s) and created {images_created} images(s)"
                )

            self._mark_missing_images_as_deleted(valid_image_ids)

            self.complete_task()
        except Exception as e:
            self.fail_task(str(e))
            raise

    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename.

        Args:
            filename: Name of the file

        Returns:
            File extension or empty string if not found
        """
        try:
            return filename.rsplit(".", 1)[1]
        except IndexError:
            logger.warning(
                f"Unable to parse file extension for file with name: {filename}"
            )
            return ""

    def _mark_missing_images_as_deleted(self, valid_image_ids: List[str]) -> None:
        """Mark images as deleted if they weren't found in the scan.

        Args:
            valid_image_ids: List of image IDs found during scan
        """
        all_images = self.image_service.list().exclude(external_id__in=valid_image_ids)
        for image in all_images.iterator():
            image.deleted = True
            image.save()

    def save_image_meta(self, image: Any) -> None:
        """Extract and save image metadata.

        Args:
            image: Image instance to extract metadata for
        """
        tag_dict = self._extract_metadata(image.file_path)
        image_meta = {
            "image": image,
            "exif": tag_dict,
        }

        try:
            existing_meta = image.meta
            existing_meta.exif = image_meta["exif"]
            self.image_metadata_service.update(existing_meta)
        except Exception:
            self.image_metadata_service.create(image_meta)

    def _extract_metadata(self, image_path: str) -> Dict[str, Any]:
        """Extract EXIF metadata from an image file.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary of EXIF tags and values
        """
        tag_dict = {}
        with PIL_Image.open(image_path) as img_pil:
            exif_data = img_pil.getexif()

            for k, v in exif_data.items():
                try:
                    tag_dict[TAGS.get(k, k)] = self._cast_to_json_compatible(v)
                except Exception as e:
                    logger.warning(
                        f"Failed to parse all metadata for image: {image_path}, error: {e}"
                    )
        return tag_dict

    def _cast_to_json_compatible(self, value: Any) -> Any:
        """Convert EXIF values to JSON-compatible types.

        Args:
            value: EXIF value to convert

        Returns:
            JSON-compatible representation of the value
        """
        if isinstance(value, TiffImagePlugin.IFDRational):
            return float(value)
        elif isinstance(value, tuple):
            return tuple(self._cast_to_json_compatible(t) for t in value)
        elif isinstance(value, bytes):
            return value.decode(errors="replace")
        elif isinstance(value, dict):
            return {k: self._cast_to_json_compatible(v) for k, v in value.items()}
        return value
