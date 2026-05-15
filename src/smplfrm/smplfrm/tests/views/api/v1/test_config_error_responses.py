from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class TestConfigErrorResponsesFix(TestCase):
    """Unit tests for ConfigViewSet.apply() error handling fix.

    These tests verify that the fix correctly sanitizes error responses,
    logs exceptions server-side, and preserves successful behavior.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/configs/apply"

    @patch("smplfrm.views.api.v1.config.ConfigService.apply_preset")
    def test_value_error_returns_sanitized_message(self, mock_apply_preset):
        """Test that ValueError returns HTTP 400 with sanitized error message."""
        internal_error = "Active config is already custom. Use PUT to update it."
        mock_apply_preset.side_effect = ValueError(internal_error)

        response = self.client.post(self.url, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"], "Unable to apply preset configuration"
        )

    @patch("smplfrm.views.api.v1.config.ConfigService.apply_preset")
    def test_value_error_does_not_expose_internal_details(self, mock_apply_preset):
        """Test that ValueError response does NOT contain internal error details."""
        internal_error = (
            "Config limit of 10 reached. "
            "Delete an existing config or select a custom one."
        )
        mock_apply_preset.side_effect = ValueError(internal_error)

        response = self.client.post(self.url, format="json")

        # Verify internal details are NOT in the response
        self.assertNotIn("limit of 10", response.data["detail"])
        self.assertNotIn("Delete an existing config", response.data["detail"])
        self.assertNotIn("already custom", response.data["detail"])
        self.assertNotIn("PUT", response.data["detail"])
        # Verify only the sanitized message is present
        self.assertEqual(
            response.data["detail"], "Unable to apply preset configuration"
        )

    @patch("smplfrm.views.api.v1.config.logger")
    @patch("smplfrm.views.api.v1.config.ConfigService.apply_preset")
    def test_value_error_logs_original_exception(self, mock_apply_preset, mock_logger):
        """Test that ValueError triggers logger.error with the original exception and exc_info=True."""
        internal_error = "Database constraint violation: config_name_unique"
        mock_apply_preset.side_effect = ValueError(internal_error)

        response = self.client.post(self.url, format="json")

        # Verify logger.error was called with the correct parameters
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args

        # Check the log message format
        self.assertEqual(call_args[0][0], "Config apply_preset error: %s")
        # Check the exception is passed
        self.assertIsInstance(call_args[0][1], ValueError)
        self.assertEqual(str(call_args[0][1]), internal_error)
        # Check exc_info=True is set
        self.assertTrue(call_args[1].get("exc_info"))

    @patch("smplfrm.views.api.v1.config.ConfigService.apply_preset")
    def test_successful_preset_application_unchanged(self, mock_apply_preset):
        """Test that successful preset application still returns HTTP 200 with config data."""
        from smplfrm.models import Config

        # Create a mock config object with actual Config model fields
        mock_config = Config(
            external_id="test-config-123",
            name="preset_default",
            description="Test preset configuration",
            is_active=True,
            display_date=True,
            display_clock=True,
        )
        mock_apply_preset.return_value = mock_config

        response = self.client.post(self.url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify the response contains config data
        self.assertIn("id", response.data)
        self.assertIn("name", response.data)
        self.assertIn("is_active", response.data)
