from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

from smplfrm.models import Plugin


class TestWeatherView(TestCase):

    def setUp(self):
        self.client = APIClient()

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_weather_endpoint_returns_display_data(self, mock_plugin_cls):
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "current_temp": "72 °F",
            "current_low_temp": "55°F",
            "current_high_temp": "80°F",
        }

        response = self.client.get("/api/v1/plugins/weather")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["current_temp"], "72 °F")
        self.assertEqual(data["current_low_temp"], "55°F")
        self.assertEqual(data["current_high_temp"], "80°F")

    @patch("smplfrm.plugins.weather.views.logger")
    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_value_error_returns_sanitized_message(self, mock_plugin_cls, mock_logger):
        """Test that ValueError returns HTTP 400 with sanitized error message."""
        mock_plugin = mock_plugin_cls.return_value
        internal_error = "API key expired: weather_service_key_12345"
        mock_plugin.get_for_display.side_effect = ValueError(internal_error)

        response = self.client.get("/api/v1/plugins/weather")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertEqual(data["error"], "Unable to retrieve weather data")

    @patch("smplfrm.plugins.weather.views.logger")
    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_value_error_does_not_expose_internal_details(
        self, mock_plugin_cls, mock_logger
    ):
        """Test that ValueError response does NOT contain internal error details."""
        mock_plugin = mock_plugin_cls.return_value
        internal_error = (
            "Database connection failed: invalid credentials for weather_api_user"
        )
        mock_plugin.get_for_display.side_effect = ValueError(internal_error)

        response = self.client.get("/api/v1/plugins/weather")

        data = response.json()
        # Verify internal details are NOT in the response
        self.assertNotIn("Database connection", data["error"])
        self.assertNotIn("weather_api_user", data["error"])
        self.assertNotIn("invalid credentials", data["error"])
        # Verify only the sanitized message is present
        self.assertEqual(data["error"], "Unable to retrieve weather data")

    @patch("smplfrm.plugins.weather.views.logger")
    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_value_error_logs_original_exception(self, mock_plugin_cls, mock_logger):
        """Test that ValueError triggers logger.error with the original exception and exc_info=True."""
        mock_plugin = mock_plugin_cls.return_value
        internal_error = "Connection timeout: weather.api.example.com"
        mock_plugin.get_for_display.side_effect = ValueError(internal_error)

        response = self.client.get("/api/v1/plugins/weather")

        # Verify logger.error was called with the correct parameters
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args

        # Check the log message format
        self.assertEqual(call_args[0][0], "Weather plugin error: %s")
        # Check the exception is passed
        self.assertIsInstance(call_args[0][1], ValueError)
        self.assertEqual(str(call_args[0][1]), internal_error)
        # Check exc_info=True is set
        self.assertTrue(call_args[1].get("exc_info"))

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_successful_weather_retrieval_unchanged(self, mock_plugin_cls):
        """Test that successful weather data retrieval still returns HTTP 200 with weather data."""
        mock_plugin = mock_plugin_cls.return_value
        weather_data = {
            "current_temp": "68 °F",
            "current_low_temp": "52°F",
            "current_high_temp": "75°F",
            "location": "San Francisco",
        }
        mock_plugin.get_for_display.return_value = weather_data

        response = self.client.get("/api/v1/plugins/weather")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data, weather_data)
