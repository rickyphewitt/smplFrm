import logging
from typing import Any, Dict, Tuple

import cv2
import numpy as np
from PIL import Image as PIL_Image
from PIL.ExifTags import TAGS
from django.conf import settings

from smplfrm.models import Image

logger = logging.getLogger(__name__)


class ImageManipulationService:
    """Service for image manipulation and display operations."""

    def display(
        self, image: Image, window_height: int = 100, window_width: int = 100
    ) -> np.ndarray:
        """Display an image scaled to fit within specified dimensions.

        Args:
            image: Image instance to display
            window_height: Target window height in pixels
            window_width: Target window width in pixels

        Returns:
            Encoded image as numpy array
        """
        return self._display_image(image, window_height, window_width)

    def _display_image(
        self, image: Image, window_height: int, window_width: int
    ) -> np.ndarray:
        """Internal method to display and scale an image.

        Args:
            image: Image instance to display
            window_height: Target window height
            window_width: Target window width

        Returns:
            Scaled and encoded image
        """
        image_metadata = self._extract_metadata(image.file_path)
        return self._scale(
            image, window_height, window_width, image_meta=image_metadata
        )

    def _scale(
        self,
        image: Image,
        window_height: int,
        window_width: int,
        image_meta: Dict[str, Any] = None,
    ) -> np.ndarray:
        """Scale an image to fit within target dimensions.

        Args:
            image: Image instance to scale
            window_height: Target window height
            window_width: Target window width
            image_meta: Optional image metadata dictionary

        Returns:
            Scaled image as encoded numpy array
        """
        if image_meta is None:
            image_meta = {}

        image_ext = image.file_path.rsplit(".", 1)[1]
        img = cv2.imread(image.file_path)

        from smplfrm.services.config_service import ConfigService

        fill_mode = ConfigService().load_config().image_fill_mode

        if fill_mode == "blur":
            resized_img = self._scale_with_blur_background(
                img, window_width, window_height
            )
        elif fill_mode == "zoom_to_fill":
            resized_img = self._scale_with_zoom_to_fill(
                img, window_width, window_height
            )
        else:
            resized_img = self._scale_with_border(img, window_width, window_height)

        logger.info(f"Resized Image: {image.name}")
        _, enc_image = cv2.imencode(ext=f".{image_ext}", img=resized_img)
        return enc_image

    def _scale_with_blur_background(
        self, img: np.ndarray, window_width: int, window_height: int
    ) -> np.ndarray:
        """Scale image with blurred background fill.

        Args:
            img: Source image
            window_width: Target width
            window_height: Target height

        Returns:
            Scaled image with blurred background
        """
        image_h, image_w = img.shape[:2]

        if window_height == 0 or window_width == 0:
            return img

        # Calculate scaled dimensions maintaining aspect ratio
        scale_height, scale_width = self._determine_scaled_dimensions(
            window_width, window_height, image_w, image_h
        )

        # Resize main image
        resized_main = cv2.resize(
            img, (scale_width, scale_height), interpolation=cv2.INTER_AREA
        )

        # Create blurred background
        background = cv2.resize(img, (window_width, window_height))
        background = cv2.GaussianBlur(background, (51, 51), 0)
        background = cv2.convertScaleAbs(background, alpha=0.6, beta=0)

        # Calculate position to center main image
        y_offset = (window_height - scale_height) // 2
        x_offset = (window_width - scale_width) // 2

        # Overlay main image on blurred background
        background[
            y_offset : y_offset + scale_height, x_offset : x_offset + scale_width
        ] = resized_main

        return background

    def _scale_with_zoom_to_fill(
        self, img: np.ndarray, window_width: int, window_height: int
    ) -> np.ndarray:
        """Scale image by zooming and cropping to fill viewport.

        Args:
            img: Source image
            window_width: Target width
            window_height: Target height

        Returns:
            Cropped and scaled image filling entire viewport
        """
        image_h, image_w = img.shape[:2]

        if window_height == 0 or window_width == 0:
            return img

        # Calculate aspect ratios
        target_aspect = window_width / window_height
        image_aspect = image_w / image_h

        # Zoom to fill (crop to fit)
        if image_aspect > target_aspect:
            # Image is wider, scale by height and crop width
            new_height = window_height
            new_width = int(window_height * image_aspect)
        else:
            # Image is taller, scale by width and crop height
            new_width = window_width
            new_height = int(window_width / image_aspect)

        # Resize image
        resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)

        # Center crop to target dimensions
        y_offset = (new_height - window_height) // 2
        x_offset = (new_width - window_width) // 2

        cropped = resized[
            y_offset : y_offset + window_height, x_offset : x_offset + window_width
        ]

        return cropped

    def _scale_with_border(
        self, img: np.ndarray, window_width: int, window_height: int
    ) -> np.ndarray:
        """Scale image with border fill (original behavior).

        Args:
            img: Source image
            window_width: Target width
            window_height: Target height

        Returns:
            Scaled image with borders
        """
        image_h, image_w = img.shape[:2]
        padding = 0

        if window_height == 0 or window_width == 0:
            return img

        target_width = int(window_width) - padding
        target_height = int(window_height) - padding

        scale_height_size, scale_width_size = self._determine_scaled_dimensions(
            target_width, target_height, image_w, image_h
        )
        vert_border, horz_border = self._determine_border(
            scale_width_size, scale_height_size, target_width, target_height
        )

        resized_img = cv2.resize(
            img, (scale_width_size, scale_height_size), interpolation=cv2.INTER_AREA
        )
        resized_img = cv2.copyMakeBorder(
            resized_img,
            horz_border,
            horz_border,
            vert_border,
            vert_border,
            cv2.BORDER_REPLICATE,
            value=(0, 0, 0, 100),
        )

        return resized_img

    def _determine_scaled_dimensions(
        self, target_width: int, target_height: int, image_w: int, image_h: int
    ) -> Tuple[int, int]:
        """Determine scaled dimensions to fit image within target size.

        Args:
            target_width: Target width in pixels
            target_height: Target height in pixels
            image_w: Original image width
            image_h: Original image height

        Returns:
            Tuple of (scaled_height, scaled_width)
        """
        portrait_viewport = target_height > target_width
        portrait_image = image_h > image_w

        scale_height_size = target_height
        scale_width_size = target_width

        if (portrait_viewport and portrait_image) or (
            not portrait_viewport and portrait_image
        ):
            scale_width_size = self._scale_by(target_height, image_w, image_h)
        elif (portrait_viewport and not portrait_image) or (
            not portrait_viewport and not portrait_image
        ):
            scale_height_size = self._scale_by(target_width, image_h, image_w)

        if scale_height_size > target_height:
            scale_width_size = self._scale_by(target_height, image_w, image_h)
            scale_height_size = target_height
        elif scale_width_size > target_width:
            scale_height_size = self._scale_by(target_width, image_h, image_w)
            scale_width_size = target_width

        return scale_height_size, scale_width_size

    def _determine_border(
        self, scale_width: int, scale_height: int, target_width: int, target_height: int
    ) -> Tuple[int, int]:
        """Calculate border sizes to center scaled image.

        Args:
            scale_width: Scaled image width
            scale_height: Scaled image height
            target_width: Target width
            target_height: Target height

        Returns:
            Tuple of (vertical_border, horizontal_border)
        """
        vertical_border = 0
        horizontal_border = 0

        if scale_width < target_width:
            vertical_border = target_width - scale_width
            vertical_border = int(vertical_border / 2)

        if scale_height < target_height:
            horizontal_border = target_height - scale_height
            horizontal_border = int(horizontal_border / 2)

        return vertical_border, horizontal_border

    def _scale_by(self, scale_to: int, size_1: int, size_2: int) -> int:
        """Calculate scaled dimension maintaining aspect ratio.

        Args:
            scale_to: Target size to scale to
            size_1: First dimension (width or height)
            size_2: Second dimension (width or height)

        Returns:
            Scaled dimension as integer
        """
        return int(scale_to * size_1 / size_2)

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
                tag_dict[TAGS.get(k, k)] = v

        return tag_dict
