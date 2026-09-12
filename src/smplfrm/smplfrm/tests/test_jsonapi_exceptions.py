"""Tests for consolidated JSON:API exception handler.

The handler produces JSON:API compliant error responses for all exceptions,
sanitizes internal details, and logs unexpected errors exactly once.
"""

import logging
from unittest.mock import Mock, patch

from django.test import TestCase, RequestFactory
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from smplfrm.jsonapi.exceptions import (
    JsonApiError,
    WeatherUnavailableError,
    InvalidQueryParameterError,
    jsonapi_exception_handler,
)


class JsonApiExceptionHandlerTest(TestCase):
    """Test consolidated JSON:API exception handler."""

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get("/api/v1/test")
        self.view = APIView()
        self.context = {"view": self.view, "request": self.request}

    def test_jsonapi_error_returns_errors_array(self):
        """JsonApiError subclasses return top-level errors array."""
        exc = WeatherUnavailableError()
        response = jsonapi_exception_handler(exc, self.context)

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", response.data)
        self.assertIsInstance(response.data["errors"], list)
        self.assertEqual(len(response.data["errors"]), 1)

        error = response.data["errors"][0]
        self.assertEqual(error["status"], "400")
        self.assertEqual(error["code"], "weather_unavailable")
        self.assertIn("detail", error)

    def test_invalid_query_parameter_error_format(self):
        """InvalidQueryParameterError formats with parameter name."""
        exc = InvalidQueryParameterError("sort")
        response = jsonapi_exception_handler(exc, self.context)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = response.data["errors"][0]
        self.assertEqual(error["code"], "invalid_query_parameter")
        self.assertIn("sort", error["detail"])

    def test_drf_not_found_exception_formatted_as_jsonapi(self):
        """DRF NotFound exception is reformatted to JSON:API errors array."""
        exc = NotFound(detail="Resource not found")
        response = jsonapi_exception_handler(exc, self.context)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("errors", response.data)
        error = response.data["errors"][0]
        self.assertEqual(error["status"], "404")
        self.assertEqual(error["code"], "not_found")
        self.assertEqual(error["detail"], "Resource not found")

    def test_drf_permission_denied_formatted_as_jsonapi(self):
        """DRF PermissionDenied is reformatted to JSON:API."""
        exc = PermissionDenied(detail="Access denied")
        response = jsonapi_exception_handler(exc, self.context)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        error = response.data["errors"][0]
        self.assertEqual(error["status"], "403")
        self.assertEqual(error["code"], "forbidden")
        self.assertEqual(error["detail"], "Access denied")

    def test_drf_validation_error_with_field_errors(self):
        """DRF ValidationError with field errors includes source pointers."""
        exc = ValidationError({"email": ["Invalid email format"]})
        response = jsonapi_exception_handler(exc, self.context)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = response.data["errors"][0]
        self.assertEqual(error["status"], "400")
        self.assertEqual(error["code"], "validation_error")
        self.assertIn("source", error)
        self.assertEqual(error["source"]["pointer"], "/data/attributes/email")

    def test_drf_validation_error_with_non_field_errors(self):
        """DRF ValidationError with non_field_errors."""
        exc = ValidationError({"non_field_errors": ["Invalid data"]})
        response = jsonapi_exception_handler(exc, self.context)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = response.data["errors"][0]
        self.assertEqual(error["detail"], "Invalid data")

    @patch("smplfrm.jsonapi.exceptions.logger")
    def test_unexpected_exception_logs_exactly_once(self, mock_logger):
        """Unexpected exceptions are logged exactly once at ERROR level."""
        exc = ValueError("Unexpected database failure")
        response = jsonapi_exception_handler(exc, self.context)

        # Verify response is generic 500
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        error = response.data["errors"][0]
        self.assertEqual(error["status"], "500")
        self.assertEqual(error["code"], "internal_error")
        self.assertEqual(error["detail"], "An unexpected error occurred")

        # Verify logging happened exactly once
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        self.assertIn("Unexpected database failure", str(call_args))
        # Verify exc_info=True was passed for traceback
        self.assertTrue(call_args[1].get("exc_info"))

    def test_unexpected_exception_sanitizes_internal_details(self):
        """Unexpected exceptions don't leak internal details in response."""
        exc = ValueError("Database connection failed at /var/lib/db.sqlite")
        response = jsonapi_exception_handler(exc, self.context)

        error_detail = response.data["errors"][0]["detail"]
        # Should NOT contain internal paths or exception message
        self.assertEqual(error_detail, "An unexpected error occurred")
        self.assertNotIn("/var/lib", error_detail)
        self.assertNotIn("Database connection", error_detail)

    def test_multiple_validation_errors_in_single_response(self):
        """Multiple field errors result in multiple error objects."""
        exc = ValidationError(
            {"email": ["Invalid format"], "username": ["Already exists"]}
        )
        response = jsonapi_exception_handler(exc, self.context)

        self.assertEqual(len(response.data["errors"]), 2)
        error_details = [e["detail"] for e in response.data["errors"]]
        self.assertIn("Invalid format", error_details)
        self.assertIn("Already exists", error_details)

    def test_handler_returns_none_for_unhandled_cases(self):
        """Handler can return None to delegate to next handler in chain."""
        # This shouldn't happen with our implementation, but test the contract
        # Our handler should always return a Response, never None
        exc = ValueError("test")
        response = jsonapi_exception_handler(exc, self.context)
        self.assertIsNotNone(response)
        self.assertIsInstance(response, Response)


class ExceptionSanitizationTest(TestCase):
    """Test that errors never leak sensitive information."""

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get("/api/v1/test")
        self.context = {"view": APIView(), "request": self.request}

    def test_no_filesystem_paths_in_errors(self):
        """Error responses never contain filesystem paths."""
        exc = IOError("Failed to read /home/user/.env")
        response = jsonapi_exception_handler(exc, self.context)

        response_str = str(response.data)
        self.assertNotIn("/home", response_str)
        self.assertNotIn(".env", response_str)

    def test_no_sql_details_in_errors(self):
        """Error responses never contain SQL or schema details."""
        exc = Exception("IntegrityError: UNIQUE constraint failed: users.email")
        response = jsonapi_exception_handler(exc, self.context)

        response_str = str(response.data)
        self.assertNotIn("IntegrityError", response_str)
        self.assertNotIn("UNIQUE constraint", response_str)
        self.assertNotIn("users.email", response_str)

    def test_no_stack_traces_in_errors(self):
        """Error responses never contain stack traces."""
        exc = RuntimeError("Failed in view.py line 42")
        response = jsonapi_exception_handler(exc, self.context)

        response_str = str(response.data)
        self.assertNotIn("line 42", response_str)
        self.assertNotIn("view.py", response_str)
        self.assertNotIn("Traceback", response_str)
