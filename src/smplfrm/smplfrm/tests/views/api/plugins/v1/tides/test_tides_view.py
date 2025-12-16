from unittest.mock import patch

from django.test import TestCase
from smplfrm.services import ImageMetadataService, ImageService
from smplfrm.services import LibraryService
from smplfrm.views.api.v1.images import Images as imageView


from smplfrm.plugins.tides import TidesPlugin


class TestImagesMetadata(TestCase):

    @patch("smplfrm.plugins.tides.tides.TidesPlugin")
    def setUp(self, mock_tides_plugin):
        self.uri = "/api/v1/plugins/tides"
        self.service = TidesPlugin()
        self.service.get_tide_data = TestTidesPlugin.get_test_data
        self.service = mock_spotify_service
        self.tide_data_success = {
            "1759280820000": {"type": "H", "value": 5.78},
            "1759308240000": {"type": "L", "value": 0.78},
            "1759334820000": {"type": "H", "value": 4.833},
            "1759351260000": {"type": "L", "value": 3.891},
        }
