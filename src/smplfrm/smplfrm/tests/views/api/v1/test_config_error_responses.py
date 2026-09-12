from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class TestConfigCreateErrorResponses(TestCase):
    """Unit tests for ConfigViewSet.create() error handling.

    These tests verify that the create endpoint correctly sanitizes error responses,
    logs exceptions server-side, and preserves successful behavior.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/configs"

    @patch("smplfrm.views.api.v1.config.ConfigService.create")
    def test_value_error_returns_error_message(self, mock_create):
        """Test that ValueError returns HTTP 400 with JSON:API errors array."""
        error_msg = "Config limit of 10 reached. Delete an existing config first."
        mock_create.side_effect = ValueError(error_msg)

        create_data = {
            "data": {
                "type": "configs",
                "attributes": {"display_date": True},
            }
        }

        response = self.client.post(
            self.url, create_data, content_type="application/vnd.api+json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn("errors", data)
        self.assertEqual(len(data["errors"]), 1)
        error = data["errors"][0]
        self.assertEqual(error["status"], "400")
        self.assertEqual(error["code"], "validation_error")
        self.assertEqual(error["detail"], error_msg)

    @patch("smplfrm.views.api.v1.config.logger")
    @patch("smplfrm.views.api.v1.config.ConfigService.create")
    def test_value_error_logs_original_exception(self, mock_create, mock_logger):
        """Test that ValueError triggers logger.error with the original exception."""
        error_msg = "Config limit exceeded"
        mock_create.side_effect = ValueError(error_msg)

        create_data = {
            "data": {
                "type": "configs",
                "attributes": {"display_date": True},
            }
        }

        response = self.client.post(
            self.url, create_data, content_type="application/vnd.api+json"
        )

        # Verify logger.error was called
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        # Check exc_info=True is set
        self.assertTrue(call_args[1].get("exc_info"))

    @patch("smplfrm.views.api.v1.config.ConfigService.create")
    def test_successful_create_returns_201(self, mock_create):
        """Test that successful create returns HTTP 201 with config data."""
        from smplfrm.models import Config

        mock_config = Config(
            external_id="test-config-123",
            name="custom-20260101",
            description="",
            is_active=True,
            display_date=True,
            display_clock=True,
        )
        mock_create.return_value = mock_config

        create_data = {
            "data": {
                "type": "configs",
                "attributes": {"display_date": True, "is_active": True},
            }
        }

        response = self.client.post(
            self.url, create_data, content_type="application/vnd.api+json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIn("data", data)
        self.assertEqual(data["data"]["type"], "configs")
        self.assertIn("attributes", data["data"])
