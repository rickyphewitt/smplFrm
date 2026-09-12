"""Tests for the consolidated JSON:API exception handler.

This module tests the global exception handler configured in settings.py.
All exceptions are formatted as JSON:API errors arrays.
"""

from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.exceptions import NotFound, ValidationError

from smplfrm.jsonapi.exceptions import jsonapi_exception_handler


class TestConsolidatedExceptionHandler(TestCase):
    """Tests for the global DRF exception handler."""

    def _make_context(self):
        return {"view": MagicMock(__class__=MagicMock(__name__="TestView"))}

    def test_drf_not_found_returns_jsonapi_errors(self):
        """DRF NotFound exceptions are formatted as JSON:API errors array."""
        context = self._make_context()
        exc = NotFound()

        response = jsonapi_exception_handler(exc, context)

        self.assertEqual(response.status_code, 404)
        self.assertIn("errors", response.data)
        self.assertIsInstance(response.data["errors"], list)
        error = response.data["errors"][0]
        self.assertEqual(error["status"], "404")
        self.assertEqual(error["code"], "not_found")

    def test_validation_error_returns_jsonapi_format(self):
        """Validation errors are formatted with JSON:API structure."""
        context = self._make_context()
        exc = ValidationError({"name": ["This field is required."]})

        response = jsonapi_exception_handler(exc, context)

        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.data)
        error = response.data["errors"][0]
        self.assertEqual(error["code"], "validation_error")
        self.assertIn("source", error)

    def test_unhandled_exception_returns_generic_500(self):
        """Unhandled exceptions return a generic 500 with no internal details."""
        context = self._make_context()
        exc = RuntimeError("connection pool exhausted")

        response = jsonapi_exception_handler(exc, context)

        self.assertEqual(response.status_code, 500)
        self.assertIn("errors", response.data)
        error = response.data["errors"][0]
        self.assertEqual(error["detail"], "An unexpected error occurred")
        self.assertEqual(error["code"], "internal_error")

    def test_unhandled_exception_does_not_leak_details(self):
        """The generic 500 response must not contain the original error message."""
        context = self._make_context()
        exc = RuntimeError("secret database password in error msg")

        response = jsonapi_exception_handler(exc, context)

        response_text = str(response.data)
        self.assertNotIn("secret", response_text)
        self.assertNotIn("database", response_text)
        self.assertNotIn("password", response_text)

    @patch("smplfrm.jsonapi.exceptions.logger")
    def test_unhandled_exception_is_logged(self, mock_logger):
        """Unhandled exceptions are logged at ERROR level with exc_info."""
        context = self._make_context()
        exc = RuntimeError("something broke")

        jsonapi_exception_handler(exc, context)

        mock_logger.error.assert_called_once()
        call_kwargs = mock_logger.error.call_args[1]
        self.assertTrue(call_kwargs.get("exc_info"))

    @patch("smplfrm.jsonapi.exceptions.logger")
    def test_drf_known_exceptions_are_not_logged_as_unexpected(self, mock_logger):
        """DRF-handled exceptions should not trigger unexpected error logging."""
        context = self._make_context()
        exc = NotFound()

        jsonapi_exception_handler(exc, context)

        # DRF exceptions don't trigger the "Unhandled exception" log path
        # They're reformatted but not logged as unexpected errors
        mock_logger.error.assert_not_called()
