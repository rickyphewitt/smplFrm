"""Unit tests for JSON:API infrastructure module.

Tests the shared components used by all JSON:API endpoints:
- Renderer media type
- Parser media type
- Exception handling and error formatting
- Strict query parameter validation
"""

from django.test import TestCase, RequestFactory
from rest_framework import status
from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
    ValidationError,
    Throttled,
)
from rest_framework.request import Request
from rest_framework.views import APIView
from unittest.mock import MagicMock

from smplfrm.jsonapi import (
    JsonApiRenderer,
    JsonApiParser,
    JsonApiError,
    WeatherUnavailableError,
    InvalidQueryParameterError,
    InternalError,
    jsonapi_exception_handler,
    StrictQueryMixin,
)


class TestJsonApiRenderer(TestCase):
    """Test JSON:API renderer configuration."""

    def test_media_type_is_jsonapi(self):
        """Renderer declares application/vnd.api+json media type."""
        renderer = JsonApiRenderer()
        self.assertEqual(renderer.media_type, "application/vnd.api+json")

    def test_format_is_vnd_api_json(self):
        """Renderer format identifier is set correctly."""
        renderer = JsonApiRenderer()
        self.assertEqual(renderer.format, "vnd.api+json")


class TestJsonApiParser(TestCase):
    """Test JSON:API parser configuration."""

    def test_media_type_is_jsonapi(self):
        """Parser accepts application/vnd.api+json media type."""
        parser = JsonApiParser()
        self.assertEqual(parser.media_type, "application/vnd.api+json")


class TestJsonApiExceptions(TestCase):
    """Test custom JSON:API exception classes."""

    def test_weather_unavailable_error_defaults(self):
        """WeatherUnavailableError has correct defaults."""
        exc = WeatherUnavailableError()
        self.assertEqual(exc.status_code, 400)
        self.assertEqual(exc.code, "weather_unavailable")
        self.assertEqual(str(exc.detail), "Unable to retrieve weather data")

    def test_invalid_query_parameter_error_with_param_name(self):
        """InvalidQueryParameterError includes parameter name in detail."""
        exc = InvalidQueryParameterError("include")
        self.assertEqual(exc.status_code, 400)
        self.assertEqual(exc.code, "invalid_query_parameter")
        self.assertIn("include", str(exc.detail))

    def test_invalid_query_parameter_error_without_param_name(self):
        """InvalidQueryParameterError works without parameter name."""
        exc = InvalidQueryParameterError()
        self.assertEqual(exc.code, "invalid_query_parameter")
        self.assertEqual(str(exc.detail), "Invalid query parameter")

    def test_internal_error_defaults(self):
        """InternalError has correct defaults."""
        exc = InternalError()
        self.assertEqual(exc.status_code, 500)
        self.assertEqual(exc.code, "internal_error")
        self.assertEqual(str(exc.detail), "An unexpected error occurred")

    def test_custom_jsonapi_error(self):
        """Custom JsonApiError with custom detail and code."""
        exc = JsonApiError(detail="Custom message", code="custom_code")
        self.assertEqual(exc.code, "custom_code")
        self.assertEqual(str(exc.detail), "Custom message")


class TestJsonApiExceptionHandler(TestCase):
    """Test JSON:API exception handler."""

    def setUp(self):
        self.factory = RequestFactory()
        self.context = {
            "view": MagicMock(),
            "request": Request(self.factory.get("/test")),
        }

    def test_handles_weather_unavailable_error(self):
        """Handler produces correct response for WeatherUnavailableError."""
        exc = WeatherUnavailableError()
        response = jsonapi_exception_handler(exc, self.context)

        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.data)
        self.assertEqual(len(response.data["errors"]), 1)

        error = response.data["errors"][0]
        self.assertEqual(error["status"], "400")
        self.assertEqual(error["code"], "weather_unavailable")
        self.assertEqual(error["detail"], "Unable to retrieve weather data")

    def test_handles_invalid_query_parameter_error(self):
        """Handler produces correct response for InvalidQueryParameterError."""
        exc = InvalidQueryParameterError("sort")
        response = jsonapi_exception_handler(exc, self.context)

        self.assertEqual(response.status_code, 400)
        error = response.data["errors"][0]
        self.assertEqual(error["code"], "invalid_query_parameter")
        self.assertIn("sort", error["detail"])

    def test_handles_internal_error(self):
        """Handler produces correct response for InternalError."""
        exc = InternalError()
        response = jsonapi_exception_handler(exc, self.context)

        self.assertEqual(response.status_code, 500)
        error = response.data["errors"][0]
        self.assertEqual(error["status"], "500")
        self.assertEqual(error["code"], "internal_error")
        self.assertEqual(error["detail"], "An unexpected error occurred")

    def test_reformats_drf_not_found(self):
        """Handler reformats DRF NotFound to JSON:API format."""
        exc = NotFound("Resource not found")
        response = jsonapi_exception_handler(exc, self.context)

        self.assertEqual(response.status_code, 404)
        self.assertIn("errors", response.data)
        error = response.data["errors"][0]
        self.assertEqual(error["status"], "404")
        self.assertEqual(error["code"], "not_found")

    def test_reformats_drf_permission_denied(self):
        """Handler reformats DRF PermissionDenied to JSON:API format."""
        exc = PermissionDenied()
        response = jsonapi_exception_handler(exc, self.context)

        self.assertEqual(response.status_code, 403)
        error = response.data["errors"][0]
        self.assertEqual(error["status"], "403")
        self.assertEqual(error["code"], "forbidden")

    def test_reformats_drf_throttled(self):
        """Handler reformats DRF Throttled to JSON:API format."""
        exc = Throttled(wait=60)
        response = jsonapi_exception_handler(exc, self.context)

        self.assertEqual(response.status_code, 429)
        error = response.data["errors"][0]
        self.assertEqual(error["status"], "429")
        self.assertEqual(error["code"], "rate_limited")

    def test_reformats_drf_validation_error(self):
        """Handler reformats DRF ValidationError to JSON:API format."""
        exc = ValidationError({"name": ["This field is required."]})
        response = jsonapi_exception_handler(exc, self.context)

        self.assertEqual(response.status_code, 400)
        error = response.data["errors"][0]
        self.assertEqual(error["code"], "validation_error")
        self.assertIn("source", error)
        self.assertEqual(error["source"]["pointer"], "/data/attributes/name")

    def test_handles_unhandled_exception(self):
        """Handler catches unhandled exceptions and returns generic 500."""
        exc = RuntimeError("Something went wrong")
        response = jsonapi_exception_handler(exc, self.context)

        self.assertEqual(response.status_code, 500)
        error = response.data["errors"][0]
        self.assertEqual(error["status"], "500")
        self.assertEqual(error["code"], "internal_error")
        self.assertEqual(error["detail"], "An unexpected error occurred")
        # Original error message should NOT be in response
        self.assertNotIn("Something went wrong", str(response.data))

    def test_error_response_has_no_data_key(self):
        """Error responses must not have 'data' key."""
        exc = WeatherUnavailableError()
        response = jsonapi_exception_handler(exc, self.context)

        self.assertNotIn("data", response.data)

    def test_error_status_is_string(self):
        """Error status field must be a string per JSON:API spec."""
        exc = WeatherUnavailableError()
        response = jsonapi_exception_handler(exc, self.context)

        error = response.data["errors"][0]
        self.assertIsInstance(error["status"], str)


class TestStrictQueryMixin(TestCase):
    """Test strict query parameter validation."""

    def setUp(self):
        self.factory = RequestFactory()

    def _create_mixin_instance(self, allowed_params=None):
        """Create a test instance with StrictQueryMixin."""

        class TestView(StrictQueryMixin):
            allowed_query_params = allowed_params or set()

            def initial(self, request, *args, **kwargs):
                # Only call the validation, skip parent's initial
                self._validate_query_params(request)

        return TestView()

    def _make_request(self, path):
        """Create a DRF Request from path."""
        django_request = self.factory.get(path)
        return Request(django_request)

    def test_rejects_include_parameter(self):
        """Rejects 'include' parameter."""
        view = self._create_mixin_instance()
        request = self._make_request("/test?include=related")

        with self.assertRaises(InvalidQueryParameterError) as ctx:
            view.initial(request)

        self.assertIn("include", str(ctx.exception.detail))

    def test_rejects_sort_parameter(self):
        """Rejects 'sort' parameter."""
        view = self._create_mixin_instance()
        request = self._make_request("/test?sort=name")

        with self.assertRaises(InvalidQueryParameterError) as ctx:
            view.initial(request)

        self.assertIn("sort", str(ctx.exception.detail))

    def test_rejects_fields_sparse_fieldsets(self):
        """Rejects 'fields[...]' sparse fieldset parameters."""
        view = self._create_mixin_instance()
        request = self._make_request("/test?fields[articles]=title")

        with self.assertRaises(InvalidQueryParameterError) as ctx:
            view.initial(request)

        self.assertIn("fields[articles]", str(ctx.exception.detail))

    def test_rejects_unknown_parameter(self):
        """Rejects unknown parameters not in allowlist."""
        view = self._create_mixin_instance(allowed_params=set())
        request = self._make_request("/test?unknown=value")

        with self.assertRaises(InvalidQueryParameterError) as ctx:
            view.initial(request)

        self.assertIn("unknown", str(ctx.exception.detail))

    def test_allows_configured_parameters(self):
        """Allows parameters in the allowlist."""
        view = self._create_mixin_instance(
            allowed_params={"page[number]", "filter[status]"}
        )
        request = self._make_request("/test?page[number]=1&filter[status]=active")

        # Should not raise
        try:
            view.initial(request)
        except InvalidQueryParameterError:
            self.fail("Should not reject allowed parameters")

    def test_allows_empty_query_string(self):
        """Allows requests with no query parameters."""
        view = self._create_mixin_instance()
        request = self._make_request("/test")

        # Should not raise
        try:
            view.initial(request)
        except InvalidQueryParameterError:
            self.fail("Should not reject empty query string")

    def test_sort_allowed_when_profile_configured(self):
        """Allows sort parameter when route declares allowed profiles."""

        class TestView(StrictQueryMixin):
            allowed_query_params = {"sort"}
            allowed_sort_profiles = {"display_priority"}

            def initial(self, request, *args, **kwargs):
                self._validate_query_params(request)

        view = TestView()
        request = self._make_request("/test?sort=display_priority")

        # Should not raise
        try:
            view.initial(request)
        except InvalidQueryParameterError:
            self.fail("Should not reject allowed sort profile")

    def test_sort_rejects_unknown_profile(self):
        """Rejects sort values not in the allowed profile set."""

        class TestView(StrictQueryMixin):
            allowed_query_params = {"sort"}
            allowed_sort_profiles = {"display_priority"}

            def initial(self, request, *args, **kwargs):
                self._validate_query_params(request)

        view = TestView()
        request = self._make_request("/test?sort=unknown")

        with self.assertRaises(InvalidQueryParameterError) as ctx:
            view.initial(request)

        self.assertIn("sort", str(ctx.exception.detail))

    def test_sort_rejects_blank_value(self):
        """Rejects blank sort parameter."""

        class TestView(StrictQueryMixin):
            allowed_query_params = {"sort"}
            allowed_sort_profiles = {"display_priority"}

            def initial(self, request, *args, **kwargs):
                self._validate_query_params(request)

        view = TestView()
        request = self._make_request("/test?sort=")

        with self.assertRaises(InvalidQueryParameterError) as ctx:
            view.initial(request)

        self.assertIn("sort", str(ctx.exception.detail))

    def test_sort_rejects_comma_separated(self):
        """Rejects comma-separated sort values."""

        class TestView(StrictQueryMixin):
            allowed_query_params = {"sort"}
            allowed_sort_profiles = {"display_priority", "alphabetical"}

            def initial(self, request, *args, **kwargs):
                self._validate_query_params(request)

        view = TestView()
        request = self._make_request("/test?sort=display_priority,alphabetical")

        with self.assertRaises(InvalidQueryParameterError) as ctx:
            view.initial(request)

        self.assertIn("sort", str(ctx.exception.detail))

    def test_sort_rejects_direction_prefix(self):
        """Rejects direction-prefixed sort values."""

        class TestView(StrictQueryMixin):
            allowed_query_params = {"sort"}
            allowed_sort_profiles = {"display_priority"}

            def initial(self, request, *args, **kwargs):
                self._validate_query_params(request)

        view = TestView()
        request = self._make_request("/test?sort=-display_priority")

        with self.assertRaises(InvalidQueryParameterError) as ctx:
            view.initial(request)

        self.assertIn("sort", str(ctx.exception.detail))

    def test_sort_rejects_duplicate_param(self):
        """Rejects duplicate sort parameters."""

        class TestView(StrictQueryMixin):
            allowed_query_params = {"sort"}
            allowed_sort_profiles = {"display_priority"}

            def initial(self, request, *args, **kwargs):
                self._validate_query_params(request)

        view = TestView()
        # Django QueryDict allows multiple values for the same key
        request = self._make_request(
            "/test?sort=display_priority&sort=display_priority"
        )

        with self.assertRaises(InvalidQueryParameterError) as ctx:
            view.initial(request)

        self.assertIn("sort", str(ctx.exception.detail))

    def test_exempt_actions_skip_validation(self):
        """Actions in exempt_actions skip query validation."""

        class TestView(StrictQueryMixin):
            allowed_query_params = set()
            exempt_actions = {"display_image"}
            action = "display_image"

            def initial(self, request, *args, **kwargs):
                if self.action not in self.exempt_actions:
                    self._validate_query_params(request)

        view = TestView()
        # Request has params that would normally be rejected
        request = self._make_request("/test?width=100&height=200")

        # Should not raise because action is exempt
        try:
            view.initial(request)
        except InvalidQueryParameterError:
            self.fail("Should not validate exempt actions")

    def test_non_exempt_actions_still_validated(self):
        """Actions not in exempt_actions are still validated."""

        class TestView(StrictQueryMixin):
            allowed_query_params = set()
            exempt_actions = {"display_image"}
            action = "list"  # Not exempt

            def initial(self, request, *args, **kwargs):
                if self.action not in self.exempt_actions:
                    self._validate_query_params(request)

        view = TestView()
        request = self._make_request("/test?unknown=value")

        with self.assertRaises(InvalidQueryParameterError) as ctx:
            view.initial(request)

        self.assertIn("unknown", str(ctx.exception.detail))

    def test_allows_filter_pattern_per_jsonapi_spec(self):
        """Allows filter[] parameters per JSON:API spec."""
        view = self._create_mixin_instance(allowed_params=set())
        request = self._make_request("/test?filter[status]=active&filter[type]=image")

        # Should not raise - filter[] is always allowed per JSON:API spec
        try:
            view.initial(request)
        except InvalidQueryParameterError:
            self.fail("Should allow filter[] parameters per JSON:API spec")

    def test_allowed_filters_restricts_filter_fields(self):
        """When allowed_filters is set, only those filter fields are accepted."""

        class TestView(StrictQueryMixin):
            allowed_query_params = set()
            allowed_filters = {"status", "type"}

            def initial(self, request, *args, **kwargs):
                self._validate_query_params(request)

        view = TestView()
        # Allowed filter
        request = self._make_request("/test?filter[status]=active")
        try:
            view.initial(request)
        except InvalidQueryParameterError:
            self.fail("Should allow filter[status] when in allowed_filters")

        # Disallowed filter
        request = self._make_request("/test?filter[secret]=value")
        with self.assertRaises(InvalidQueryParameterError) as ctx:
            view.initial(request)
        self.assertIn("filter[secret]", str(ctx.exception.detail))

    def test_empty_allowed_filters_permits_all_filters(self):
        """When allowed_filters is empty (default), all filter[] params pass."""

        class TestView(StrictQueryMixin):
            allowed_query_params = set()
            allowed_filters = set()  # Empty = allow all

            def initial(self, request, *args, **kwargs):
                self._validate_query_params(request)

        view = TestView()
        request = self._make_request("/test?filter[any_field]=value&filter[other]=x")

        try:
            view.initial(request)
        except InvalidQueryParameterError:
            self.fail("Empty allowed_filters should permit all filter[] params")
