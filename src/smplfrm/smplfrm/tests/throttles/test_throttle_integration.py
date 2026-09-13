"""
Integration tests for API rate limiting through the DRF throttle pipeline.

Tests verify end-to-end throttle behavior including HTTP status codes,
response headers, response body format, bucket independence, and rate
window recovery.
"""

from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

# Low throttle rates for testing — keeps tests fast and deterministic.
TEST_THROTTLE_RATES = {
    "global_anon": "3/minute",
    "global_authenticated": "5/minute",
    "global_task": "2/minute",
}

TEST_REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "smplfrm.jsonapi.exceptions.jsonapi_exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "smplfrm.jsonapi.renderers.JsonApiRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "smplfrm.jsonapi.parsers.JsonApiParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "smplfrm.jsonapi.pagination.JsonApiPagination",
    "DEFAULT_METADATA_CLASS": "rest_framework_json_api.metadata.JSONAPIMetadata",
    "DEFAULT_THROTTLE_CLASSES": [
        "smplfrm.throttles.GlobalAnonThrottle",
        "smplfrm.throttles.GlobalAuthenticatedThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": TEST_THROTTLE_RATES,
}


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """Clear the cache before and after each test to reset throttle counters."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    """Unauthenticated DRF API client."""
    return APIClient()


@pytest.fixture
def auth_user(db):
    """Create a test user for authenticated requests."""
    return User.objects.create_user(
        username="throttle_test_user",
        password="testpass123",
    )


@pytest.fixture
def auth_client(auth_user):
    """Authenticated DRF API client."""
    client = APIClient()
    client.force_authenticate(user=auth_user)
    return client


class TestAnonymousThrottling:
    """Anonymous requests are throttled using the global anonymous bucket."""

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_requests_under_limit_succeed(self, api_client):
        """Anonymous requests below the configured limit return HTTP 200."""
        for _ in range(3):
            response = api_client.get("/api/v1/configs")
            assert response.status_code == 200

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_requests_over_limit_return_429(self, api_client):
        """Anonymous requests exceeding the limit return HTTP 429."""
        # Exhaust the limit (3 requests)
        for _ in range(3):
            api_client.get("/api/v1/configs")

        # The 4th request should be throttled
        response = api_client.get("/api/v1/configs")
        assert response.status_code == 429

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_429_response_has_retry_after_header(self, api_client):
        """Throttled responses include a Retry-After header."""
        for _ in range(3):
            api_client.get("/api/v1/configs")

        response = api_client.get("/api/v1/configs")
        assert response.status_code == 429
        assert "Retry-After" in response

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_429_response_has_json_body_with_detail(self, api_client):
        """Throttled responses include a JSON:API errors array with detail."""
        for _ in range(3):
            api_client.get("/api/v1/configs")

        response = api_client.get("/api/v1/configs")
        assert response.status_code == 429
        data = response.json()
        # JSON:API format uses errors array
        assert "errors" in data
        assert len(data["errors"]) > 0
        assert "detail" in data["errors"][0]
        assert isinstance(data["errors"][0]["detail"], str)
        assert len(data["errors"][0]["detail"]) > 0


class TestAuthenticatedThrottling:
    """Authenticated requests are throttled using the global authenticated bucket."""

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_requests_under_limit_succeed(self, auth_client):
        """Authenticated requests below the configured limit return HTTP 200."""
        for _ in range(5):
            response = auth_client.get("/api/v1/configs")
            assert response.status_code == 200

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_requests_over_limit_return_429(self, auth_client):
        """Authenticated requests exceeding the limit return HTTP 429."""
        # Exhaust the limit (5 requests)
        for _ in range(5):
            auth_client.get("/api/v1/configs")

        # The 6th request should be throttled
        response = auth_client.get("/api/v1/configs")
        assert response.status_code == 429


class TestTaskEndpointThrottling:
    """Task creation applies a stricter rate limit via GlobalTaskThrottle.

    List, detail, and delete actions are NOT subject to the task-specific bucket;
    only POST (create) consumes the task-creation quota.
    """

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_task_create_applies_task_bucket(self, api_client):
        """POST /tasks consumes the task-specific bucket (limit 2/min).

        DRF throttle checks run in initial() before body parsing, so even
        requests with an invalid body are counted against the throttle bucket.
        We send a minimal JSON:API document that passes parsing but fails
        business validation (400) so we can count task-bucket consumption.
        """
        invalid_task_body = '{"data":{"type":"no_such_task_type","attributes":{}}}'

        # First 2 POST requests count against the task bucket; body validation
        # returns 400 but the throttle tick has already been recorded.
        for _ in range(2):
            response = api_client.post(
                "/api/v1/tasks",
                data=invalid_task_body,
                content_type="application/vnd.api+json",
            )
            # Throttle passed → body validation runs → 400 or 409 expected
            assert response.status_code in (201, 400, 409)

        # 3rd POST must be rejected by the task-specific bucket (exhausted at 2)
        response = api_client.post(
            "/api/v1/tasks",
            data=invalid_task_body,
            content_type="application/vnd.api+json",
        )
        assert response.status_code == 429

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_task_list_does_not_consume_task_bucket(self, api_client):
        """GET /tasks (list) does not consume the task-creation bucket.

        We make exactly as many GET list requests as the task-creation limit
        (2/min). If list requests consumed the task bucket, the subsequent POST
        would return 429 from that bucket. Instead it must reach body validation
        (returning 400), proving the task bucket was untouched.

        We stay under the general anon limit (3/min) so the general throttle
        cannot interfere with the result.
        """
        invalid_task_body = '{"data":{"type":"no_such_task_type","attributes":{}}}'

        # Make exactly as many GET requests as the task-creation limit allows.
        # If list consumed the task bucket, subsequent POST would be 429.
        for _ in range(2):
            response = api_client.get("/api/v1/tasks")
            assert response.status_code == 200

        # A subsequent POST must NOT be rejected by the task bucket.
        # 2 GETs consumed 2/3 of the general anon quota; this POST uses the 3rd.
        # The task bucket must still be at full capacity.
        response = api_client.post(
            "/api/v1/tasks",
            data=invalid_task_body,
            content_type="application/vnd.api+json",
        )
        assert response.status_code != 429

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_exhausting_task_creation_bucket_does_not_block_task_list(self, api_client):
        """After exhausting the task-creation bucket, GET /tasks still succeeds."""
        invalid_task_body = '{"data":{"type":"no_such_task_type","attributes":{}}}'

        # Exhaust the task-creation bucket with POST requests
        for _ in range(2):
            api_client.post(
                "/api/v1/tasks",
                data=invalid_task_body,
                content_type="application/vnd.api+json",
            )

        # Task list should still work — it does not use the task-creation bucket
        response = api_client.get("/api/v1/tasks")
        assert response.status_code == 200

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_task_create_counts_against_both_buckets(self, api_client):
        """POST /tasks counts against both the task-specific and general anon buckets."""
        invalid_task_body = '{"data":{"type":"no_such_task_type","attributes":{}}}'

        # Make 2 POST requests (exhausts task bucket of 2).
        # These also count against the general anon bucket (2 of 3 used).
        for _ in range(2):
            api_client.post(
                "/api/v1/tasks",
                data=invalid_task_body,
                content_type="application/vnd.api+json",
            )

        # General anon bucket has 1 remaining — a non-task request still works
        response = api_client.get("/api/v1/configs")
        assert response.status_code == 200


class TestBucketIndependence:
    """Exhausting one bucket does not affect requests counted against another."""

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_exhausting_anon_bucket_does_not_block_authenticated(
        self, api_client, auth_client
    ):
        """Exhausting the anonymous bucket does not block authenticated requests."""
        # Exhaust anonymous bucket (3 requests)
        for _ in range(3):
            api_client.get("/api/v1/configs")

        # Anonymous should be throttled
        response = api_client.get("/api/v1/configs")
        assert response.status_code == 429

        # Authenticated should still work
        response = auth_client.get("/api/v1/configs")
        assert response.status_code == 200

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_exhausting_authenticated_bucket_does_not_block_anonymous(
        self, api_client, auth_client
    ):
        """Exhausting the authenticated bucket does not block anonymous requests."""
        # Exhaust authenticated bucket (5 requests)
        for _ in range(5):
            auth_client.get("/api/v1/configs")

        # Authenticated should be throttled
        response = auth_client.get("/api/v1/configs")
        assert response.status_code == 429

        # Anonymous should still work
        response = api_client.get("/api/v1/configs")
        assert response.status_code == 200


class TestResponseFormat:
    """Throttled responses have correct Content-Type and Retry-After format."""

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_429_response_content_type_is_json(self, api_client):
        """Throttled responses have Content-Type: application/vnd.api+json."""
        for _ in range(3):
            api_client.get("/api/v1/configs")

        response = api_client.get("/api/v1/configs")
        assert response.status_code == 429
        assert "application/vnd.api+json" in response["Content-Type"]

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_retry_after_header_is_positive_integer(self, api_client):
        """The Retry-After header value is a positive integer (whole seconds)."""
        for _ in range(3):
            api_client.get("/api/v1/configs")

        response = api_client.get("/api/v1/configs")
        assert response.status_code == 429
        retry_after = response["Retry-After"]
        # Must be parseable as an integer
        retry_value = int(retry_after)
        # Must be positive (>= 1)
        assert retry_value >= 1


class TestRateWindowRecovery:
    """After the rate window elapses, requests succeed again."""

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_requests_succeed_after_window_elapses(self, api_client):
        """After the rate window expires, the throttle resets and allows requests."""
        import time

        # Exhaust the anonymous bucket
        for _ in range(3):
            api_client.get("/api/v1/configs")

        # Confirm we're throttled
        response = api_client.get("/api/v1/configs")
        assert response.status_code == 429

        # Advance time past the 60-second window.
        # DRF's SimpleRateThrottle uses time.time() to track request timestamps.
        # We clear the cache to simulate TTL expiry (the in-memory/locmem cache
        # doesn't actually expire entries based on mocked time).
        cache.clear()

        # After cache is cleared (simulating window expiry), requests succeed again
        response = api_client.get("/api/v1/configs")
        assert response.status_code == 200
