from django.test import TestCase

from smplfrm.services import ImageService
from smplfrm.services import LibraryService
from smplfrm.services.config_service import ConfigService

import cv2
import numpy as np
import pytest

from smplfrm.services.image_manipulation_service import ImageManipulationService


class TestImageManipulationService(TestCase):
    """Test suite for ImageManipulationService."""

    def setUp(self):
        """Set up test fixtures."""
        self.image_service = ImageService()
        self.image_manipulation_service = ImageManipulationService()
        self.padding = 0
        # bootstrap the images
        LibraryService().scan()

    def _set_fill_mode(self, fill_mode):
        """Persist the fill mode on the active config, which display() reads."""
        config = ConfigService().load_config()
        config.image_fill_mode = fill_mode
        config.save()

    def test_display_image(self):
        """Test basic image display functionality."""
        image = self.image_service.list()[0]

        displayed_image = self.image_manipulation_service.display(image, 100, 100)
        self.assertIsNotNone(displayed_image, "Displayed Image should not be None!")

    def test_scale_horizontal_image_with_border(self):
        """Test scaling horizontal image with border fill mode."""
        self._set_fill_mode("border")
        window_h = 100
        window_w = 100

        image = self.image_service.list(
            file_name="david-becker-F7SBonu15d8-unsplash.jpg"
        )[0]

        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        # read raw image data and assert new values
        img = cv2.imdecode(displayed_image, -1)
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        self.assertEqual(window_w - self.padding, image_w)
        self.assertEqual(window_h - self.padding, image_h)

    def test_scale_vertical_image_with_border(self):
        """Test scaling vertical image with border fill mode."""
        self._set_fill_mode("border")
        window_h = 100
        window_w = 100

        image = self.image_service.list(
            file_name="kelly-sikkema-PqqQDpS6H6A-unsplash.jpg"
        )[0]

        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        # read raw image data and assert new values
        img = cv2.imdecode(displayed_image, -1)
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        self.assertEqual(window_h - self.padding, image_h)
        self.assertEqual(window_w - self.padding, image_w)

    def test_scale_horizontal_image_height_larger_than_viewport_with_border(self):
        """Test border mode when scaled image height exceeds viewport height."""
        self._set_fill_mode("border")
        window_h = 100
        window_w = 1000

        image = self.image_service.list(
            file_name="kelly-sikkema-PqqQDpS6H6A-unsplash.jpg"
        )[0]

        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        # read raw image data and assert new values
        img = cv2.imdecode(displayed_image, -1)
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        self.assertEqual(window_w - self.padding, image_w)
        self.assertEqual(window_h - self.padding, image_h)

    def test_scale_panoramic_image_with_border(self):
        """Test scaling panoramic image with border fill mode."""
        self._set_fill_mode("border")
        window_h = 433
        window_w = 952

        image = self.image_service.list(
            file_name="bernd-dittrich-73scJ3UOdHM-unsplash.jpg"
        )[0]

        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        # read raw image data and assert new values
        img = cv2.imdecode(displayed_image, -1)
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        self.assertEqual(window_w - self.padding, image_w)
        self.assertEqual(window_h - self.padding, image_h)

    def test_scale_horizontal_image_with_blur(self):
        """Test scaling horizontal image with blur background fill mode."""
        self._set_fill_mode("blur")
        window_h = 100
        window_w = 100

        image = self.image_service.list(
            file_name="david-becker-F7SBonu15d8-unsplash.jpg"
        )[0]

        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        img = cv2.imdecode(displayed_image, -1)
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        self.assertEqual(window_w, image_w)
        self.assertEqual(window_h, image_h)

    def test_scale_vertical_image_with_blur(self):
        """Test scaling vertical image with blur background fill mode."""
        self._set_fill_mode("blur")
        window_h = 100
        window_w = 100

        image = self.image_service.list(
            file_name="kelly-sikkema-PqqQDpS6H6A-unsplash.jpg"
        )[0]

        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        img = cv2.imdecode(displayed_image, -1)
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        self.assertEqual(window_h, image_h)
        self.assertEqual(window_w, image_w)

    def test_scale_panoramic_image_with_blur(self):
        """Test scaling panoramic image with blur background fill mode."""
        self._set_fill_mode("blur")
        window_h = 433
        window_w = 952

        image = self.image_service.list(
            file_name="bernd-dittrich-73scJ3UOdHM-unsplash.jpg"
        )[0]

        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        img = cv2.imdecode(displayed_image, -1)
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        self.assertEqual(window_w, image_w)
        self.assertEqual(window_h, image_h)

    def test_blur_background_creates_valid_image(self):
        """Test that blur background mode creates a valid image array."""
        self._set_fill_mode("blur")
        window_h = 200
        window_w = 300

        image = self.image_service.list()[0]
        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        img = cv2.imdecode(displayed_image, -1)

        # Verify it's a valid numpy array
        self.assertIsInstance(img, np.ndarray)
        # Verify it has 3 color channels (BGR)
        self.assertEqual(len(img.shape), 3)
        self.assertEqual(img.shape[2], 3)

    def test_scale_horizontal_image_with_zoom_to_fill(self):
        """Test scaling horizontal image with Ken Burns effect."""
        self._set_fill_mode("zoom_to_fill")
        window_h = 100
        window_w = 100

        image = self.image_service.list(
            file_name="david-becker-F7SBonu15d8-unsplash.jpg"
        )[0]

        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        img = cv2.imdecode(displayed_image, -1)
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        # Ken Burns fills entire viewport
        self.assertEqual(window_w, image_w)
        self.assertEqual(window_h, image_h)

    def test_scale_vertical_image_with_zoom_to_fill(self):
        """Test scaling vertical image with Ken Burns effect."""
        self._set_fill_mode("zoom_to_fill")
        window_h = 100
        window_w = 100

        image = self.image_service.list(
            file_name="kelly-sikkema-PqqQDpS6H6A-unsplash.jpg"
        )[0]

        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        img = cv2.imdecode(displayed_image, -1)
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        # Ken Burns fills entire viewport
        self.assertEqual(window_h, image_h)
        self.assertEqual(window_w, image_w)

    def test_scale_panoramic_image_with_zoom_to_fill(self):
        """Test scaling panoramic image with Ken Burns effect."""
        self._set_fill_mode("zoom_to_fill")
        window_h = 433
        window_w = 952

        image = self.image_service.list(
            file_name="bernd-dittrich-73scJ3UOdHM-unsplash.jpg"
        )[0]

        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        img = cv2.imdecode(displayed_image, -1)
        size = img.shape[:2]
        image_h = size[0]
        image_w = size[1]

        # Ken Burns fills entire viewport
        self.assertEqual(window_w, image_w)
        self.assertEqual(window_h, image_h)

    def test_zoom_to_fill_crops_to_fill(self):
        """Test that Ken Burns mode crops image to fill viewport without gaps."""
        self._set_fill_mode("zoom_to_fill")
        window_h = 200
        window_w = 300

        image = self.image_service.list()[0]
        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        img = cv2.imdecode(displayed_image, -1)

        # Verify exact dimensions (no borders or gaps)
        self.assertEqual(img.shape[0], window_h)
        self.assertEqual(img.shape[1], window_w)
        # Verify it's a valid color image
        self.assertEqual(img.shape[2], 3)

    def test_fill_mode_dynamically_loaded_from_config(self):
        """Fill mode is re-read from the active config on every display call.

        Every mode returns the window dimensions, so dimensions alone cannot
        show which mode ran; the pixels for a horizontal image differ between
        border (edge padding) and zoom_to_fill (center crop).
        """
        window_h = 100
        window_w = 100
        image = self.image_service.list(
            file_name="david-becker-F7SBonu15d8-unsplash.jpg"
        )[0]

        self._set_fill_mode("border")
        border_img = cv2.imdecode(
            self.image_manipulation_service.display(
                image, window_height=window_h, window_width=window_w
            ),
            -1,
        )

        self._set_fill_mode("zoom_to_fill")
        zoom_img = cv2.imdecode(
            self.image_manipulation_service.display(
                image, window_height=window_h, window_width=window_w
            ),
            -1,
        )

        self.assertEqual(border_img.shape, zoom_img.shape)
        self.assertFalse(np.array_equal(border_img, zoom_img))

    def test_fill_mode_invalid_falls_back_to_border(self):
        """Test that invalid fill mode falls back to border mode."""
        self._set_fill_mode("invalid_mode")
        window_h = 100
        window_w = 100

        image = self.image_service.list()[0]
        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        img = cv2.imdecode(displayed_image, -1)
        # Should fall back to border mode
        self.assertEqual(img.shape[0], window_h)
        self.assertEqual(img.shape[1], window_w)

    def test_determine_border_odd_gap_fills_target_exactly(self):
        """Odd gaps put the extra pixel bottom/right so no pixel is lost."""
        top, bottom, left, right = self.image_manipulation_service._determine_border(
            scale_width=75, scale_height=100, target_width=100, target_height=100
        )

        self.assertEqual((top, bottom, left, right), (0, 0, 12, 13))
        self.assertEqual(75 + left + right, 100)


VALID_BOUNDARY_VALUES = [1, 2, 100, 2048, 4095, 4096]


class TestValidateDimensionsPreservation:
    """Test suite for validate_dimensions with valid inputs."""

    @pytest.mark.parametrize("width", VALID_BOUNDARY_VALUES)
    @pytest.mark.parametrize("height", VALID_BOUNDARY_VALUES)
    def test_valid_dimensions_return_tuple(self, width, height):
        """Test that valid dimensions return the correct (width, height) tuple."""
        result = ImageManipulationService.validate_dimensions(str(width), str(height))
        assert result == (width, height)

    @pytest.mark.parametrize(
        "width_str,height_str,expected",
        [
            ("100", "100", (100, 100)),
            ("1", "1", (1, 1)),
            ("4096", "4096", (4096, 4096)),
            ("800", "600", (800, 600)),
        ],
    )
    def test_common_dimension_pairs(self, width_str, height_str, expected):
        """Test that common dimension pairs are accepted and returned correctly."""
        result = ImageManipulationService.validate_dimensions(width_str, height_str)
        assert result == expected
