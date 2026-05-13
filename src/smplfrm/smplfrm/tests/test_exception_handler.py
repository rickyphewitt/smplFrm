from unittest.mock import patch, MagicMock

from django.test import TestCase
from rest_framework.exceptions import NotFound, ValidationError

from smplfrm.exception_handler import sanitized_exception_handler


class TestSanitizedExceptionHandler(TestCase):
    """Tests for the global DRF exception handler."""

    def _make_context(self):
        return {"view": MagicMock(__class__=MagicMock(__name__="TestView"))}

    def test_drf_known_exceptions_pass_through(self):
        """DRF-recognized exceptions (404, 400, etc.) are returned as-is."""
        context = self._make_context()
        exc = NotFound()

        response = sanitized_exception_handler(exc, context)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(str(response.data["detail"]), "Not found.")

    def test_validation_error_passes_through(self):
        """Validation errors retain their field-level detail."""
        context = self._make_context()
        exc = ValidationError({"name": ["This field is required."]})

        response = sanitized_exception_handler(exc, context)

        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data)

    def test_unhandled_exception_returns_generic_500(self):
        """Unhandled exceptions return a generic 500 with no internal details."""
        context = self._make_context()
        exc = RuntimeError("connection pool exhausted")

        response = sanitized_exception_handler(exc, context)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["detail"], "An internal error occurred")

    def test_unhandled_exception_does_not_leak_details(self):
        """The generic 500 response must not contain the original error message."""
        context = self._make_context()
        exc = RuntimeError("secret database password in error msg")

        response = sanitized_exception_handler(exc, context)

        response_text = str(response.data)
        self.assertNotIn("secret", response_text)
        self.assertNotIn("database", response_text)
        self.assertNotIn("password", response_text)

    @patch("smplfrm.exception_handler.logger")
    def test_unhandled_exception_is_logged(self, mock_logger):
        """Unhandled exceptions are logged at ERROR level with exc_info."""
        context = self._make_context()
        exc = RuntimeError("something broke")

        sanitized_exception_handler(exc, context)

        mock_logger.error.assert_called_once()
        call_kwargs = mock_logger.error.call_args[1]
        self.assertTrue(call_kwargs.get("exc_info"))

    @patch("smplfrm.exception_handler.logger")
    def test_drf_known_exceptions_are_not_logged(self, mock_logger):
        """DRF-handled exceptions should not trigger our error logging."""
        context = self._make_context()
        exc = NotFound()

        sanitized_exception_handler(exc, context)

        mock_logger.error.assert_not_called()
