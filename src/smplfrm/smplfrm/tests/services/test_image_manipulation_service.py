from django.test import TestCase, override_settings

from smplfrm.services import ImageService
from smplfrm.services import LibraryService

import cv2
import numpy as np

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

    def test_display_image(self):
        """Test basic image display functionality."""
        image = self.image_service.list()[0]

        displayed_image = self.image_manipulation_service.display(image, 100, 100)
        self.assertIsNotNone(displayed_image, "Displayed Image should not be None!")

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="border")
    def test_scale_horizontal_image_with_border(self):
        """Test scaling horizontal image with border fill mode."""
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

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="border")
    def test_scale_vertical_image_with_border(self):
        """Test scaling vertical image with border fill mode."""
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

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="border")
    def test_scale_horizontal_image_height_larger_than_viewport_with_border(self):
        """Test border mode when scaled image height exceeds viewport height."""
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

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="border")
    def test_scale_panoramic_image_with_border(self):
        """Test scaling panoramic image with border fill mode."""
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

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="blur")
    def test_scale_horizontal_image_with_blur(self):
        """Test scaling horizontal image with blur background fill mode."""
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

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="blur")
    def test_scale_vertical_image_with_blur(self):
        """Test scaling vertical image with blur background fill mode."""
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

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="blur")
    def test_scale_panoramic_image_with_blur(self):
        """Test scaling panoramic image with blur background fill mode."""
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

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="blur")
    def test_blur_background_creates_valid_image(self):
        """Test that blur background mode creates a valid image array."""
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

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="zoom_to_fill")
    def test_scale_horizontal_image_with_zoom_to_fill(self):
        """Test scaling horizontal image with Ken Burns effect."""
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

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="zoom_to_fill")
    def test_scale_vertical_image_with_zoom_to_fill(self):
        """Test scaling vertical image with Ken Burns effect."""
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

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="zoom_to_fill")
    def test_scale_panoramic_image_with_zoom_to_fill(self):
        """Test scaling panoramic image with Ken Burns effect."""
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

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="zoom_to_fill")
    def test_zoom_to_fill_crops_to_fill(self):
        """Test that Ken Burns mode crops image to fill viewport without gaps."""
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

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="border")
    def test_fill_mode_dynamically_loaded_border(self):
        """Test that SMPL_FRM_IMAGE_FILL_MODE is loaded dynamically, not cached."""
        window_h = 100
        window_w = 100

        image = self.image_service.list()[0]
        displayed_image = self.image_manipulation_service.display(
            image, window_height=window_h, window_width=window_w
        )

        img = cv2.imdecode(displayed_image, -1)
        # Border mode should match window dimensions
        self.assertEqual(img.shape[0], window_h)
        self.assertEqual(img.shape[1], window_w)

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="invalid_mode")
    def test_fill_mode_invalid_falls_back_to_border(self):
        """Test that invalid fill mode falls back to border mode."""
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
