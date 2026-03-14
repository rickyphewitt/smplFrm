import os

from django.test import TestCase
from django.test.utils import override_settings

from smplfrm.services import LibraryService

test_library = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "library"))
]


@override_settings(SMPL_FRM_LIBRARY_DIRS=test_library)
class TestLibraryScanProgress(TestCase):
    """Test suite for LibraryService.scan progress reporting."""

    def test_scan_reports_progress(self):
        """Test that scan calls on_progress per image found."""
        service = LibraryService()
        progress_values = []

        service.scan(on_progress=lambda pct: progress_values.append(pct))

        # Test library has 3 images
        self.assertEqual(len(progress_values), 3)
        self.assertEqual(progress_values[0], 33)
        self.assertEqual(progress_values[1], 66)
        self.assertEqual(progress_values[2], 100)

    def test_scan_works_without_callback(self):
        """Test that scan works when on_progress is None."""
        service = LibraryService()
        service.scan()
        # No error means success
