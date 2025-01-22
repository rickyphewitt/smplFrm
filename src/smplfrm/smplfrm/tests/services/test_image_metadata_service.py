
from django.test import TestCase
from smplfrm.services import ImageService
from smplfrm.services import LibraryService
from smplfrm.services import ImageMetadataService
import datetime


class TestImageService(TestCase):
    def setUp(self):
        self.image_metadata_service = ImageMetadataService()
        self.image_service = ImageService()
        # bootstrap the images
        LibraryService().scan()



    def test_metadata_and_date_is_populated_for_images(self):


        for image in self.image_service.list():
            image_meta = self.image_metadata_service.read_by_image_id(image.external_id)
            self.assertIsNotNone(image_meta)
            self.assertIsNotNone(image_meta.exif)



    def test_datetime_parsing(self):


        parsable_dates = [
            ("2014:10:18 13:49:12", datetime.datetime(2014, 10, 18, 13, 49, 12)),
            ("2014:07:25 19:39:59.283", datetime.datetime(2014, 7, 25, 19, 39, 59, 283000)),
            ("2014:03:19 18:15:53+00:00", datetime.datetime(2014, 3, 19, 18, 15, 53, tzinfo=datetime.timezone.utc)),
            ("UnparsableDate", "UnparsableDate")
        ]

        for date, expected_date in parsable_dates:
            metadata = {'DateTime': date}
            parsed_datetime = self.image_metadata_service.parse_date_from_meta(metadata)
            self.assertEqual(expected_date, parsed_datetime)


    def test_datetime_folder_structure(self):
        import datetime
        image = self.image_service.list(file_name="bernd-dittrich-73scJ3UOdHM-unsplash.jpg")[0]
        parsed_datetime = self.image_metadata_service.parse_date_from_path(image.file_path)
        self.assertEqual(datetime.datetime(2024, 11, 2, 0, 0, 1, 999), parsed_datetime)
