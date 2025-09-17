import os

from django.test import TestCase

from src.smplfrm.smplfrm.services import ImageService, LibraryService
from django.test.utils import override_settings

test_library = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "library"))
]


@override_settings(SMPL_FRM_LIBRARY_DIRS=test_library)
class TestLibraryService(TestCase):
    def setUp(self):

        self.library_service = LibraryService()
        self.image_service = ImageService()

    def test_scan(self):
        self.library_service.scan()

        images = self.image_service.list(deleted=False)

        self.assertIsNotNone(images, "Images should not be None")
        self.assertEqual(len(images), 3, f"Expected 3 images but found {len(images)}")

        # mark images as deleted that do exist on the file system and
        # verify scan marks them as non deleted
        valid_image = images[0]
        valid_image.deleted = True
        valid_image.save()

        # add images that are not present on the filesystem and verify
        # scan marks them as deleteXd
        image_data = {
            "name": "should_be_deleted",
            "file_path": "./filePathDoesNotExist/",
            "file_name": "fileNameDoesNotExist.jpg",
        }
        created_image = self.image_service.create(image_data)
        self.assertFalse(created_image.deleted, "Image should not be deleted")

        self.library_service.scan()
        deleted_image = self.image_service.read(
            ext_id=created_image.external_id, deleted=True
        )
        undeleted_image = self.image_service.read(ext_id=valid_image.external_id)

        # verify metadata exif
        image_meta = undeleted_image.meta
        self.assertIsNotNone(image_meta)
        self.assertIsNotNone(image_meta.exif)
