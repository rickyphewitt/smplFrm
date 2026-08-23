"""JSON:API contract tests for Weather endpoint.

Tests the Weather JSON:API contract:
- Endpoint: /api/v1/plugins/weather/current
- Resource type: weather
- ID: "current" (singleton)
- Attributes: temperature, temperature_scale, daily_low, daily_low_scale,
              daily_high, daily_high_scale (all strings)
- Media type: application/vnd.api+json
- Errors: JSON:API errors array with status, code, detail
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch


class TestWeatherJsonApiSuccess(TestCase):
    """Test successful Weather responses conform to JSON:API contract."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/plugins/weather/current"

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_success_returns_jsonapi_media_type(self, mock_plugin_cls):
        """Response Content-Type must be application/vnd.api+json."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "temperature": "72",
            "temperature_scale": "F",
            "daily_low": "55",
            "daily_low_scale": "F",
            "daily_high": "80",
            "daily_high_scale": "F",
        }

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.api+json",
            "Response must use JSON:API media type",
        )

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_success_has_top_level_data(self, mock_plugin_cls):
        """Response must have top-level 'data' key, not bare object."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "temperature": "72",
            "temperature_scale": "F",
            "daily_low": "55",
            "daily_low_scale": "F",
            "daily_high": "80",
            "daily_high_scale": "F",
        }

        response = self.client.get(self.url)
        data = response.json()

        self.assertIn("data", data, "Response must have top-level 'data' key")
        self.assertNotIn("temperature", data, "Attributes must not be at top level")

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_success_resource_type_is_weather(self, mock_plugin_cls):
        """Resource type must be 'weather'."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "temperature": "72",
            "temperature_scale": "F",
            "daily_low": "55",
            "daily_low_scale": "F",
            "daily_high": "80",
            "daily_high_scale": "F",
        }

        response = self.client.get(self.url)
        data = response.json()

        self.assertEqual(
            data["data"]["type"],
            "weather",
            "Resource type must be 'weather'",
        )

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_success_resource_id_is_current(self, mock_plugin_cls):
        """Singleton resource ID must be 'current'."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "temperature": "72",
            "temperature_scale": "F",
            "daily_low": "55",
            "daily_low_scale": "F",
            "daily_high": "80",
            "daily_high_scale": "F",
        }

        response = self.client.get(self.url)
        data = response.json()

        self.assertEqual(
            data["data"]["id"],
            "current",
            "Singleton ID must be 'current'",
        )

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_success_attributes_structure(self, mock_plugin_cls):
        """Attributes must contain approved fields with value/scale separation."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "temperature": "72",
            "temperature_scale": "F",
            "daily_low": "55",
            "daily_low_scale": "F",
            "daily_high": "80",
            "daily_high_scale": "F",
        }

        response = self.client.get(self.url)
        data = response.json()

        attrs = data["data"]["attributes"]
        required_fields = [
            "temperature",
            "temperature_scale",
            "daily_low",
            "daily_low_scale",
            "daily_high",
            "daily_high_scale",
        ]
        for field in required_fields:
            self.assertIn(field, attrs, f"Missing required attribute: {field}")

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_success_attributes_are_strings(self, mock_plugin_cls):
        """All attribute values must be strings."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "temperature": "72",
            "temperature_scale": "F",
            "daily_low": "55",
            "daily_low_scale": "F",
            "daily_high": "80",
            "daily_high_scale": "F",
        }

        response = self.client.get(self.url)
        data = response.json()

        attrs = data["data"]["attributes"]
        for key, value in attrs.items():
            self.assertIsInstance(
                value, str, f"Attribute '{key}' must be a string, got {type(value)}"
            )

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_success_temperature_values_extracted(self, mock_plugin_cls):
        """Temperature values must be numeric strings with separate scale."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "temperature": "72",
            "temperature_scale": "F",
            "daily_low": "55",
            "daily_low_scale": "F",
            "daily_high": "80",
            "daily_high_scale": "F",
        }

        response = self.client.get(self.url)
        data = response.json()

        attrs = data["data"]["attributes"]
        self.assertEqual(attrs["temperature"], "72")
        self.assertEqual(attrs["temperature_scale"], "F")
        self.assertEqual(attrs["daily_low"], "55")
        self.assertEqual(attrs["daily_low_scale"], "F")
        self.assertEqual(attrs["daily_high"], "80")
        self.assertEqual(attrs["daily_high_scale"], "F")

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_success_celsius_scale(self, mock_plugin_cls):
        """Celsius temperatures must use 'C' scale."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "temperature": "22",
            "temperature_scale": "C",
            "daily_low": "13",
            "daily_low_scale": "C",
            "daily_high": "27",
            "daily_high_scale": "C",
        }

        response = self.client.get(self.url)
        data = response.json()

        attrs = data["data"]["attributes"]
        self.assertEqual(attrs["temperature"], "22")
        self.assertEqual(attrs["temperature_scale"], "C")
        self.assertEqual(attrs["daily_low"], "13")
        self.assertEqual(attrs["daily_low_scale"], "C")
        self.assertEqual(attrs["daily_high"], "27")
        self.assertEqual(attrs["daily_high_scale"], "C")

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_success_no_legacy_fields(self, mock_plugin_cls):
        """Response must not contain legacy field names."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "temperature": "72",
            "temperature_scale": "F",
            "daily_low": "55",
            "daily_low_scale": "F",
            "daily_high": "80",
            "daily_high_scale": "F",
        }

        response = self.client.get(self.url)
        data = response.json()

        attrs = data["data"]["attributes"]
        legacy_fields = ["current_temp", "current_low_temp", "current_high_temp"]
        for field in legacy_fields:
            self.assertNotIn(
                field, attrs, f"Legacy field '{field}' must not appear in attributes"
            )

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_success_no_included_key(self, mock_plugin_cls):
        """Response must not have 'included' key (compound documents not supported)."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "temperature": "72",
            "temperature_scale": "F",
            "daily_low": "55",
            "daily_low_scale": "F",
            "daily_high": "80",
            "daily_high_scale": "F",
        }

        response = self.client.get(self.url)
        data = response.json()

        self.assertNotIn("included", data, "Compound documents not supported")


class TestWeatherJsonApiErrors(TestCase):
    """Test Weather error responses conform to JSON:API contract."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/plugins/weather/current"

    @patch("smplfrm.plugins.weather.views.logger")
    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_value_error_returns_jsonapi_errors_array(
        self, mock_plugin_cls, mock_logger
    ):
        """ValueError must return JSON:API errors array, not bare error object."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.side_effect = ValueError("Config error")

        response = self.client.get(self.url)
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", data, "Error response must have 'errors' array")
        self.assertIsInstance(data["errors"], list)
        self.assertNotIn("data", data, "Error response must not have 'data'")

    @patch("smplfrm.plugins.weather.views.logger")
    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_value_error_has_required_error_fields(self, mock_plugin_cls, mock_logger):
        """Error object must have status, code, and detail fields."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.side_effect = ValueError("Config error")

        response = self.client.get(self.url)
        data = response.json()

        error = data["errors"][0]
        self.assertIn("status", error)
        self.assertIn("code", error)
        self.assertIn("detail", error)

    @patch("smplfrm.plugins.weather.views.logger")
    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_value_error_status_is_string(self, mock_plugin_cls, mock_logger):
        """Error status must be a string per JSON:API spec."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.side_effect = ValueError("Config error")

        response = self.client.get(self.url)
        data = response.json()

        error = data["errors"][0]
        self.assertEqual(error["status"], "400")
        self.assertIsInstance(error["status"], str)

    @patch("smplfrm.plugins.weather.views.logger")
    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_value_error_code_is_weather_unavailable(
        self, mock_plugin_cls, mock_logger
    ):
        """ValueError must use 'weather_unavailable' error code."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.side_effect = ValueError("Config error")

        response = self.client.get(self.url)
        data = response.json()

        error = data["errors"][0]
        self.assertEqual(error["code"], "weather_unavailable")

    @patch("smplfrm.plugins.weather.views.logger")
    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_value_error_detail_is_sanitized(self, mock_plugin_cls, mock_logger):
        """Error detail must be sanitized, not expose internal message."""
        mock_plugin = mock_plugin_cls.return_value
        internal_message = "API key expired: secret_key_12345"
        mock_plugin.get_for_display.side_effect = ValueError(internal_message)

        response = self.client.get(self.url)
        data = response.json()

        error = data["errors"][0]
        self.assertEqual(error["detail"], "Unable to retrieve weather data")
        self.assertNotIn("secret_key", error["detail"])
        self.assertNotIn("API key", error["detail"])

    @patch("smplfrm.plugins.weather.views.logger")
    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_value_error_returns_jsonapi_media_type(self, mock_plugin_cls, mock_logger):
        """Error response must use JSON:API media type."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.side_effect = ValueError("Config error")

        response = self.client.get(self.url)

        self.assertEqual(response["Content-Type"], "application/vnd.api+json")

    @patch("smplfrm.plugins.weather.views.logger")
    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_unexpected_error_returns_500_with_generic_message(
        self, mock_plugin_cls, mock_logger
    ):
        """Unexpected exceptions must return 500 with generic error."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.side_effect = RuntimeError("Unexpected failure")

        response = self.client.get(self.url)
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("errors", data)
        error = data["errors"][0]
        self.assertEqual(error["status"], "500")
        self.assertEqual(error["code"], "internal_error")
        self.assertEqual(error["detail"], "An unexpected error occurred")

    @patch("smplfrm.plugins.weather.views.logger")
    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_unexpected_error_logs_once_with_exc_info(
        self, mock_plugin_cls, mock_logger
    ):
        """Unexpected exceptions must be logged exactly once with exc_info=True."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.side_effect = RuntimeError("Unexpected failure")

        response = self.client.get(self.url)

        # Find ERROR level calls
        error_calls = [
            c for c in mock_logger.error.call_args_list if c[1].get("exc_info")
        ]
        self.assertEqual(
            len(error_calls), 1, "Must log exactly once at ERROR with exc_info=True"
        )

    @patch("smplfrm.plugins.weather.views.logger")
    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_unexpected_error_does_not_expose_details(
        self, mock_plugin_cls, mock_logger
    ):
        """Unexpected error response must not expose internal details."""
        mock_plugin = mock_plugin_cls.return_value
        internal_message = "Database connection lost: db_password_xyz"
        mock_plugin.get_for_display.side_effect = RuntimeError(internal_message)

        response = self.client.get(self.url)
        response_text = response.content.decode("utf-8")

        self.assertNotIn("Database", response_text)
        self.assertNotIn("db_password", response_text)
        self.assertNotIn("connection", response_text)


class TestWeatherJsonApiQueryPolicy(TestCase):
    """Test Weather strict query parameter policy."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/plugins/weather/current"

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_unknown_query_param_rejected(self, mock_plugin_cls):
        """Unknown query parameters must be rejected with 400."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "temperature": "72",
            "temperature_scale": "F",
            "daily_low": "55",
            "daily_low_scale": "F",
            "daily_high": "80",
            "daily_high_scale": "F",
        }

        response = self.client.get(f"{self.url}?unknown=value")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn("errors", data)
        error = data["errors"][0]
        self.assertEqual(error["code"], "invalid_query_parameter")

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_include_param_rejected(self, mock_plugin_cls):
        """'include' parameter must be rejected (compound documents not supported)."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "temperature": "72",
            "temperature_scale": "F",
            "daily_low": "55",
            "daily_low_scale": "F",
            "daily_high": "80",
            "daily_high_scale": "F",
        }

        response = self.client.get(f"{self.url}?include=location")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        error = data["errors"][0]
        self.assertEqual(error["code"], "invalid_query_parameter")

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_fields_param_rejected(self, mock_plugin_cls):
        """'fields[...]' sparse fieldsets must be rejected."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "temperature": "72",
            "temperature_scale": "F",
            "daily_low": "55",
            "daily_low_scale": "F",
            "daily_high": "80",
            "daily_high_scale": "F",
        }

        response = self.client.get(f"{self.url}?fields[weather]=temperature")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        error = data["errors"][0]
        self.assertEqual(error["code"], "invalid_query_parameter")

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_sort_param_rejected(self, mock_plugin_cls):
        """'sort' parameter must be rejected."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "temperature": "72",
            "temperature_scale": "F",
            "daily_low": "55",
            "daily_low_scale": "F",
            "daily_high": "80",
            "daily_high_scale": "F",
        }

        response = self.client.get(f"{self.url}?sort=temperature")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        error = data["errors"][0]
        self.assertEqual(error["code"], "invalid_query_parameter")

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_query_validation_before_domain_access(self, mock_plugin_cls):
        """Query validation must run before calling plugin (domain access)."""
        mock_plugin = mock_plugin_cls.return_value

        response = self.client.get(f"{self.url}?invalid=param")

        # Plugin should never be called when query is invalid
        mock_plugin.get_for_display.assert_not_called()


class TestWeatherJsonApiMediaNegotiation(TestCase):
    """Test Weather media type negotiation."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/plugins/weather/current"

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_accept_jsonapi_returns_jsonapi(self, mock_plugin_cls):
        """Accept: application/vnd.api+json returns JSON:API response."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "temperature": "72",
            "temperature_scale": "F",
            "daily_low": "55",
            "daily_low_scale": "F",
            "daily_high": "80",
            "daily_high_scale": "F",
        }

        response = self.client.get(self.url, HTTP_ACCEPT="application/vnd.api+json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/vnd.api+json")

    @patch("smplfrm.plugins.weather.views.WeatherPlugin")
    def test_accept_wildcard_returns_jsonapi(self, mock_plugin_cls):
        """Accept: */* returns JSON:API response (default)."""
        mock_plugin = mock_plugin_cls.return_value
        mock_plugin.get_for_display.return_value = {
            "temperature": "72",
            "temperature_scale": "F",
            "daily_low": "55",
            "daily_low_scale": "F",
            "daily_high": "80",
            "daily_high_scale": "F",
        }

        response = self.client.get(self.url, HTTP_ACCEPT="*/*")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/vnd.api+json")
