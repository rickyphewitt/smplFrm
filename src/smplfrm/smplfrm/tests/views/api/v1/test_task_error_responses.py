import json
from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class TestTaskErrorResponses(TestCase):
    """Tests for sanitized error responses in TaskViewSet.create()."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/tasks"
        # JSON:API format with polymorphic type
        self.valid_payload = {"data": {"type": "clear_cache_tasks", "attributes": {}}}

    # --- IntegrityError handling ---

    @patch("smplfrm.views.api.v1.tasks.TaskService.create")
    def test_integrity_error_returns_409_with_generic_message(self, mock_create):
        """IntegrityError returns HTTP 409 with a safe generic message."""
        mock_create.side_effect = IntegrityError(
            "UNIQUE constraint failed: smplfrm_task.task_type"
        )

        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        body = json.loads(response.content)
        self.assertIn("errors", body)
        self.assertEqual(
            body["errors"][0]["detail"], "A conflicting task already exists"
        )

    @patch("smplfrm.views.api.v1.tasks.TaskService.create")
    def test_integrity_error_does_not_leak_schema_details(self, mock_create):
        """IntegrityError response must not contain database schema information."""
        mock_create.side_effect = IntegrityError(
            "UNIQUE constraint failed: smplfrm_task.task_type"
        )

        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type="application/vnd.api+json",
        )

        response_text = response.content.decode()
        self.assertNotIn("smplfrm_task", response_text)
        self.assertNotIn("UNIQUE constraint", response_text)

    @patch("smplfrm.views.api.v1.tasks.logger")
    @patch("smplfrm.views.api.v1.tasks.TaskService.create")
    def test_integrity_error_logs_original_exception(self, mock_create, mock_logger):
        """IntegrityError triggers logger.error with the original exception."""
        exc = IntegrityError("UNIQUE constraint failed: smplfrm_task.task_type")
        mock_create.side_effect = exc

        self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type="application/vnd.api+json",
        )

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        # The original exception should be in the log arguments
        self.assertIn(exc, call_args[0])
        # exc_info=True must be passed for full traceback
        self.assertTrue(call_args[1].get("exc_info"))

    # --- Unexpected exception handling ---

    @patch("smplfrm.views.api.v1.tasks.TaskService.create")
    def test_unexpected_exception_returns_500_with_generic_message(self, mock_create):
        """Unexpected exceptions return HTTP 500 with a safe generic message."""
        mock_create.side_effect = RuntimeError("connection pool exhausted")
        self.client.raise_request_exception = False

        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("application/vnd.api+json", response["Content-Type"])
        body = json.loads(response.content)
        self.assertIn("errors", body)
        self.assertEqual(body["errors"][0]["detail"], "An internal error occurred")

    @patch("smplfrm.views.api.v1.tasks.TaskService.create")
    def test_unexpected_exception_does_not_leak_internal_details(self, mock_create):
        """Unexpected exception response must not contain internal error details."""
        mock_create.side_effect = RuntimeError("connection pool exhausted")
        self.client.raise_request_exception = False

        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type="application/vnd.api+json",
        )

        response_text = response.content.decode()
        self.assertNotIn("connection pool", response_text)
        self.assertNotIn("exhausted", response_text)
        self.assertNotIn("RuntimeError", response_text)

    @patch("smplfrm.views.api.v1.tasks.logger")
    @patch("smplfrm.views.api.v1.tasks.TaskService.create")
    def test_unexpected_exception_logs_original_exception(
        self, mock_create, mock_logger
    ):
        """Unexpected exceptions trigger logger.error with the original exception."""
        exc = RuntimeError("connection pool exhausted")
        mock_create.side_effect = exc
        self.client.raise_request_exception = False

        self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type="application/vnd.api+json",
        )

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        # The original exception should be in the log arguments
        self.assertIn(exc, call_args[0])
        # exc_info=True must be passed for full traceback
        self.assertTrue(call_args[1].get("exc_info"))

    # --- Preservation: successful creation ---

    @patch("smplfrm.celery.app")
    def test_successful_creation_returns_201_with_serialized_data(self, mock_app):
        """Successful task creation still returns HTTP 201 with serialized task."""
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_payload),
            content_type="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = json.loads(response.content)
        self.assertIn("data", body)
        self.assertEqual(body["data"]["type"], "clear_cache_tasks")
        self.assertEqual(body["data"]["attributes"]["label"], "Clear Cache")
        self.assertEqual(body["data"]["attributes"]["status"], "pending")
        self.assertEqual(body["data"]["attributes"]["progress"], 0)
        self.assertIn("id", body["data"])

    # --- Preservation: validation errors ---

    def test_invalid_input_returns_409_with_validation_errors(self):
        """Invalid task type returns HTTP 409 with JSON:API error object."""
        invalid_payload = {"data": {"type": "not-a-real-type", "attributes": {}}}
        response = self.client.post(
            self.url,
            data=json.dumps(invalid_payload),
            content_type="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        body = json.loads(response.content)
        self.assertIn("errors", body)
        self.assertIn("not-a-real-type", body["errors"][0]["detail"])
