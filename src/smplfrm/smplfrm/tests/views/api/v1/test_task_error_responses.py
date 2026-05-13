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
        self.valid_payload = {"task_type": "clear_cache"}

    # --- IntegrityError handling ---

    @patch("smplfrm.views.api.v1.tasks.TaskService.create")
    def test_integrity_error_returns_409_with_generic_message(self, mock_create):
        """IntegrityError returns HTTP 409 with a safe generic message."""
        mock_create.side_effect = IntegrityError(
            "UNIQUE constraint failed: smplfrm_task.task_type"
        )

        response = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["detail"], "A conflicting task already exists")

    @patch("smplfrm.views.api.v1.tasks.TaskService.create")
    def test_integrity_error_does_not_leak_schema_details(self, mock_create):
        """IntegrityError response must not contain database schema information."""
        mock_create.side_effect = IntegrityError(
            "UNIQUE constraint failed: smplfrm_task.task_type"
        )

        response = self.client.post(self.url, self.valid_payload, format="json")

        response_text = str(response.data)
        self.assertNotIn("smplfrm_task", response_text)
        self.assertNotIn("UNIQUE constraint", response_text)
        self.assertNotIn("task_type", response_text)

    @patch("smplfrm.views.api.v1.tasks.logger")
    @patch("smplfrm.views.api.v1.tasks.TaskService.create")
    def test_integrity_error_logs_original_exception(self, mock_create, mock_logger):
        """IntegrityError triggers logger.error with the original exception."""
        exc = IntegrityError("UNIQUE constraint failed: smplfrm_task.task_type")
        mock_create.side_effect = exc

        self.client.post(self.url, self.valid_payload, format="json")

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

        response = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response["Content-Type"], "application/json")
        body = json.loads(response.content)
        self.assertEqual(body["detail"], "An internal error occurred")

    @patch("smplfrm.views.api.v1.tasks.TaskService.create")
    def test_unexpected_exception_does_not_leak_internal_details(self, mock_create):
        """Unexpected exception response must not contain internal error details."""
        mock_create.side_effect = RuntimeError("connection pool exhausted")
        self.client.raise_request_exception = False

        response = self.client.post(self.url, self.valid_payload, format="json")

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

        self.client.post(self.url, self.valid_payload, format="json")

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
        response = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["task_type"], "clear_cache")
        self.assertEqual(response.data["task_type_label"], "Clear Cache")
        self.assertEqual(response.data["status"], "pending")
        self.assertEqual(response.data["progress"], 0)
        self.assertIn("id", response.data)

    # --- Preservation: validation errors ---

    def test_invalid_input_returns_400_with_validation_errors(self):
        """Invalid input still returns HTTP 400 with validation error details."""
        response = self.client.post(
            self.url, {"task_type": "not_a_real_type"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("task_type", response.data)
