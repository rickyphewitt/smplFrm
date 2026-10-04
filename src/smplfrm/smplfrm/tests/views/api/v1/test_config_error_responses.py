from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from smplfrm.services.config_service import ConfigLimitExceeded


class TestConfigCreateErrorResponses(TestCase):
    """Unit tests for ConfigViewSet.create() error handling.

    These tests verify that the create endpoint correctly sanitizes error responses,
    logs exceptions server-side, and preserves successful behavior.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/configs"

    @patch("smplfrm.views.api.v1.config.ConfigService.create")
    def test_config_limit_exceeded_returns_author_controlled_detail(self, mock_create):
        """ConfigLimitExceeded maps to 400 with the author-controlled detail."""
        mock_create.side_effect = ConfigLimitExceeded()

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
        self.assertEqual(error["code"], ConfigLimitExceeded.code)
        self.assertEqual(error["detail"], ConfigLimitExceeded.detail)

    @patch("smplfrm.views.api.v1.config.logger")
    @patch("smplfrm.views.api.v1.config.ConfigService.create")
    def test_config_limit_exceeded_logs_warning_without_exc_info(
        self, mock_create, mock_logger
    ):
        """ConfigLimitExceeded triggers exactly one logger.warning, no exc_info.

        This is an expected, client-triggerable condition (not a server fault),
        so it must not be logged at ERROR/exc_info=True — that severity is
        reserved for the generic exception catch-all below.
        """
        mock_create.side_effect = ConfigLimitExceeded()

        create_data = {
            "data": {
                "type": "configs",
                "attributes": {"display_date": True},
            }
        }

        self.client.post(self.url, create_data, content_type="application/vnd.api+json")

        mock_logger.warning.assert_called_once()
        mock_logger.error.assert_not_called()

    @patch("smplfrm.views.api.v1.config.ConfigService.create")
    def test_generic_exception_returns_500_without_exception_text(self, mock_create):
        """An unexpected exception with secret-bearing text returns a sanitized 500."""
        mock_create.side_effect = RuntimeError("secret database password in error msg")

        create_data = {
            "data": {
                "type": "configs",
                "attributes": {"display_date": True},
            }
        }

        response = self.client.post(
            self.url, create_data, content_type="application/vnd.api+json"
        )

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        body_text = response.content.decode()
        self.assertNotIn("secret", body_text)
        self.assertNotIn("database", body_text)
        self.assertNotIn("password", body_text)
        data = response.json()
        error = data["errors"][0]
        self.assertEqual(error["status"], "500")
        self.assertEqual(error["code"], "internal_error")

    @patch("smplfrm.views.api.v1.config.ConfigService.create")
    def test_field_bearing_value_error_returns_no_field_details(self, mock_create):
        """A ValueError naming a model field never echoes the field or type text."""
        mock_create.side_effect = ValueError(
            "Field 'image_refresh_interval' expected a number but got 'abc'"
        )

        create_data = {
            "data": {
                "type": "configs",
                "attributes": {"display_date": True},
            }
        }

        response = self.client.post(
            self.url, create_data, content_type="application/vnd.api+json"
        )

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        body_text = response.content.decode()
        self.assertNotIn("image_refresh_interval", body_text)
        self.assertNotIn("expected a number", body_text)

    @patch("smplfrm.views.api.v1.config.logger")
    @patch("smplfrm.views.api.v1.config.ConfigService.create")
    def test_generic_exception_logs_original_exception_once(
        self, mock_create, mock_logger
    ):
        """An unexpected exception triggers exactly one logger.error with exc_info=True."""
        mock_create.side_effect = RuntimeError("boom")

        create_data = {
            "data": {
                "type": "configs",
                "attributes": {"display_date": True},
            }
        }

        self.client.post(self.url, create_data, content_type="application/vnd.api+json")

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
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
