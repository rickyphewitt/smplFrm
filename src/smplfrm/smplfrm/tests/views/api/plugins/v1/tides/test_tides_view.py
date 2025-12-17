from unittest.mock import Mock, patch

from django.test import TestCase
from smplfrm.plugins.tides import TidesPlugin


class TestTidesView(TestCase):

    @patch("smplfrm.plugins.tides.tides.TidesPlugin")
    def setUp(self, mock_tides_plugin):
        self.uri = "/api/v1/plugins/tides"
        self.service = TidesPlugin()
        self.service = mock_tides_plugin
        self.tide_data_success = {
            "1759280820000": {"type": "H", "height": 5.78},
            "1759308240000": {"type": "L", "height": 0.78},
            "1759334820000": {"type": "H", "height": 4.833},
            "1759351260000": {"type": "L", "height": 3.891},
        }

    @patch("smplfrm.views.api.plugins.v1.tides.tides_view.TidesPlugin")
    def test_tides_success(self, mock_tides_plugin):
        mock_tides_instance = Mock()
        mock_tides_plugin.return_value = mock_tides_instance
        mock_tides_instance.get_for_display.return_value = self.tide_data_success

        response = self.client.get(f"{self.uri}")
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 200)
        returned_json = response.json()

        self.assertEqual(returned_json["1759280820000"]["type"], "H")
        self.assertEqual(returned_json["1759280820000"]["height"], 5.78)
        self.assertEqual(returned_json["1759308240000"]["type"], "L")
        self.assertEqual(returned_json["1759308240000"]["height"], 0.78)
        self.assertEqual(returned_json["1759334820000"]["type"], "H")
        self.assertEqual(returned_json["1759334820000"]["height"], 4.833)
        self.assertEqual(returned_json["1759351260000"]["type"], "L")
        self.assertEqual(returned_json["1759351260000"]["height"], 3.891)

    @patch("smplfrm.views.api.plugins.v1.tides.tides_view.TidesPlugin")
    def test_tides_no_tides_found(self, mock_tides_plugin):
        mock_tides_instance = Mock()
        mock_tides_plugin.return_value = mock_tides_instance
        mock_tides_instance.get_for_display.return_value = None

        response = self.client.get(f"{self.uri}")
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 200)
        returned_json = response.json()
        self.assertEqual(len(returned_json), 0)
