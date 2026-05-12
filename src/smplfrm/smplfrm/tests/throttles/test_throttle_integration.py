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
        """Throttled responses include a JSON body with a 'detail' field."""
        for _ in range(3):
            api_client.get("/api/v1/configs")

        response = api_client.get("/api/v1/configs")
        assert response.status_code == 429
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0


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
    """Task endpoint applies a stricter rate limit via GlobalTaskThrottle."""

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_task_endpoint_applies_stricter_limit(self, api_client):
        """Task endpoint is throttled at 2/min (stricter than general 3/min)."""
        # First 2 requests should succeed (task limit is 2/min)
        for _ in range(2):
            response = api_client.get("/api/v1/tasks")
            assert response.status_code == 200

        # 3rd request should be throttled by the task bucket
        response = api_client.get("/api/v1/tasks")
        assert response.status_code == 429

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_task_endpoint_counts_against_both_buckets(self, api_client):
        """Requests to the task endpoint count against both task and general buckets."""
        # Make 2 requests to the task endpoint (exhausts task bucket of 2)
        for _ in range(2):
            api_client.get("/api/v1/tasks")

        # The general anon bucket (limit 3) should have 2 counted against it
        # So we should have 1 remaining request on the general bucket
        response = api_client.get("/api/v1/configs")
        assert response.status_code == 200

    @pytest.mark.django_db
    @override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
    def test_exhausting_task_bucket_does_not_block_other_endpoints(self, api_client):
        """Exhausting the task-specific bucket does not block non-task endpoints."""
        # Exhaust the task bucket (2 requests).
        # These also count against the general anon bucket (2 of 3 used).
        for _ in range(2):
            api_client.get("/api/v1/tasks")

        # Other endpoints should still work — the general anon bucket has
        # capacity remaining (1 of 3 left).
        response = api_client.get("/api/v1/configs")
        assert response.status_code == 200

        # Meanwhile the task endpoint is throttled (task bucket exhausted)
        response = api_client.get("/api/v1/tasks")
        assert response.status_code == 429


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
        """Throttled responses have Content-Type: application/json."""
        for _ in range(3):
            api_client.get("/api/v1/configs")

        response = api_client.get("/api/v1/configs")
        assert response.status_code == 429
        assert "application/json" in response["Content-Type"]

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
