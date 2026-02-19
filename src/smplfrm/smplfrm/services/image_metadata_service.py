import logging
import re
from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta
from django.db.models import QuerySet

from smplfrm.settings import SMPL_FRM_FORCE_DATE_FROM_PATH
from smplfrm.models import ImageMetadata

from .base_service import BaseService

logger = logging.getLogger(__name__)


class ImageMetadataService(BaseService):
    """Service for managing image metadata including EXIF data and date extraction."""

    def create(self, data: Dict[str, Any]) -> ImageMetadata:
        """Create image metadata with extracted date information.

        Args:
            data: Dictionary containing image and exif data

        Returns:
            Created ImageMetadata instance
        """
        date = self.extract_date(data["image"].file_path, data["exif"])
        data["taken"] = date
        return ImageMetadata.objects.create(**data)

    def read(self, ext_id: str, deleted: bool = False) -> ImageMetadata:
        """Retrieve image metadata by external ID.

        Args:
            ext_id: External identifier
            deleted: Whether to include soft-deleted records

        Returns:
            ImageMetadata instance
        """
        return ImageMetadata.objects.get(external_id=ext_id, deleted=deleted)

    def list(self, **kwargs) -> QuerySet[ImageMetadata]:
        """List image metadata with optional filtering.

        Args:
            **kwargs: Filter parameters

        Returns:
            QuerySet of ImageMetadata instances
        """
        if kwargs:
            return ImageMetadata.objects.filter(**kwargs)
        return ImageMetadata.objects.all()

    def update(self, image_meta: ImageMetadata) -> ImageMetadata:
        """Update image metadata with refreshed date information.

        Args:
            image_meta: ImageMetadata instance to update

        Returns:
            Updated ImageMetadata instance
        """
        date = self.extract_date(image_meta.image.file_path, image_meta.exif)
        image_meta.taken = date
        image_meta.save()
        return image_meta

    def delete(self, ext_id: str) -> None:
        """Soft delete image metadata by external ID.

        Args:
            ext_id: External identifier
        """
        try:
            image_meta_to_soft_delete = ImageMetadata.objects.get(
                external_id=ext_id, deleted=False
            )
        except ImageMetadata.DoesNotExist:
            return

        image_meta_to_soft_delete.deleted = True
        image_meta_to_soft_delete.save()

    def destroy(self, ext_id: str) -> None:
        """Permanently delete image metadata from the database.

        Args:
            ext_id: External identifier
        """
        try:
            image_meta_to_destroy = ImageMetadata.objects.get(external_id=ext_id)
        except ImageMetadata.DoesNotExist:
            return

        image_meta_to_destroy.delete()

    def read_by_image_id(self, image_ext_id: str) -> ImageMetadata:
        """Retrieve image metadata by associated image external ID.

        Args:
            image_ext_id: External ID of the associated image

        Returns:
            ImageMetadata instance
        """
        return ImageMetadata.objects.get(image__external_id=image_ext_id)

    def extract_date(
        self, image_path: str, image_meta: Dict[str, Any]
    ) -> Optional[Union[datetime, str]]:
        """Extract date from image path or metadata.

        Args:
            image_path: File path of the image
            image_meta: EXIF metadata dictionary

        Returns:
            Parsed datetime object, date string, or None
        """
        if SMPL_FRM_FORCE_DATE_FROM_PATH:
            date_str = self.parse_date_from_path(image_path)
            logger.info(f"Found Date String {date_str} from path.")
            return date_str

        if "DateTime" not in image_meta:
            logger.error(
                f"Unable to Find DateTime in image meta: {image_meta}, defaulting to image name."
            )
            image_meta.update({"DateTime": "Unknown"})

        return self.parse_date_from_meta(image_meta)

    def parse_date_from_meta(
        self, image_meta: Dict[str, Any]
    ) -> Optional[Union[datetime, str]]:
        """Parse date from EXIF metadata.

        Args:
            image_meta: EXIF metadata dictionary

        Returns:
            Parsed datetime object or original string if parsing fails
        """
        manual_dt_parsing = [
            "%Y:%m:%d %H:%M:%S",  # '2014:10:18 13:49:12'
            "%Y:%m:%d %H:%M:%S.%f",  # '2014:07:25 19:39:59.283'
            "%Y:%m:%d %H:%M:%S%z",  # '2014:03:19 18:15:53+00:00'
        ]

        string_date = image_meta["DateTime"]

        for dt_format in manual_dt_parsing:
            try:
                return datetime.strptime(string_date, dt_format)
            except Exception as e:
                logger.debug(
                    f"Failed to parse DateTime '{string_date}' with format '{dt_format}': {e}"
                )

        return string_date

    def parse_date_from_path(self, path: str) -> Optional[datetime]:
        """Parse date from file path using YYYY/MM pattern.

        Args:
            path: File path containing date information

        Returns:
            Parsed datetime object or None if pattern not found
        """
        match = re.search(r"([12]\d{3}/(0[1-9]|1[0-2]))", path)
        if match:
            parsed_date = datetime.strptime(match.group(0), "%Y/%m")
            # Offset from day 1 of the month for timezone handling
            parsed_date = parsed_date + timedelta(days=1, seconds=1, microseconds=999)
            return parsed_date
        return None
