"""
Tests for custom throttle classes.

Verifies that GlobalAnonThrottle, GlobalAuthenticatedThrottle, and
GlobalTaskThrottle return correct cache keys based on request authentication
status, use the expected scope names, and fail open when Redis is unavailable.
"""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIRequestFactory

from smplfrm.throttles import (
    GlobalAnonThrottle,
    GlobalAuthenticatedThrottle,
    GlobalTaskThrottle,
)


@pytest.fixture
def factory():
    """DRF API request factory."""
    return APIRequestFactory()


@pytest.fixture
def anonymous_request(factory):
    """A GET request with an anonymous (unauthenticated) user."""
    request = factory.get("/api/v1/test/")
    user = MagicMock()
    user.is_authenticated = False
    request.user = user
    return request


@pytest.fixture
def authenticated_request(factory):
    """A GET request with an authenticated user."""
    request = factory.get("/api/v1/test/")
    user = MagicMock()
    user.is_authenticated = True
    request.user = user
    return request


class TestGlobalAnonThrottleCacheKey:
    """GlobalAnonThrottle returns a fixed key for anonymous requests, None for authenticated."""

    def test_returns_fixed_key_for_anonymous_request(self, anonymous_request):
        """Anonymous requests get a fixed global cache key."""
        throttle = GlobalAnonThrottle()
        key = throttle.get_cache_key(anonymous_request, view=None)
        assert key is not None
        assert "global_anon" in key
        assert "global" in key

    def test_returns_none_for_authenticated_request(self, authenticated_request):
        """Authenticated requests are skipped (returns None)."""
        throttle = GlobalAnonThrottle()
        key = throttle.get_cache_key(authenticated_request, view=None)
        assert key is None

    def test_returns_none_when_user_is_authenticated_object(self, factory):
        """Authenticated user object causes throttle to be skipped."""
        request = factory.get("/api/v1/test/")
        user = MagicMock()
        user.is_authenticated = True
        request.user = user
        throttle = GlobalAnonThrottle()
        key = throttle.get_cache_key(request, view=None)
        assert key is None


class TestGlobalAuthenticatedThrottleCacheKey:
    """GlobalAuthenticatedThrottle returns a fixed key for authenticated requests, None for anonymous."""

    def test_returns_fixed_key_for_authenticated_request(self, authenticated_request):
        """Authenticated requests get a fixed global cache key."""
        throttle = GlobalAuthenticatedThrottle()
        key = throttle.get_cache_key(authenticated_request, view=None)
        assert key is not None
        assert "global_authenticated" in key
        assert "global" in key

    def test_returns_none_for_anonymous_request(self, anonymous_request):
        """Anonymous requests are skipped (returns None)."""
        throttle = GlobalAuthenticatedThrottle()
        key = throttle.get_cache_key(anonymous_request, view=None)
        assert key is None

    def test_returns_none_when_user_not_authenticated(self, factory):
        """User with is_authenticated=False causes throttle to be skipped."""
        request = factory.get("/api/v1/test/")
        user = MagicMock()
        user.is_authenticated = False
        request.user = user
        throttle = GlobalAuthenticatedThrottle()
        key = throttle.get_cache_key(request, view=None)
        assert key is None


class TestGlobalTaskThrottleCacheKey:
    """GlobalTaskThrottle always returns a fixed key regardless of auth status."""

    def test_returns_fixed_key_for_anonymous_request(self, anonymous_request):
        """Anonymous requests get a fixed global cache key."""
        throttle = GlobalTaskThrottle()
        key = throttle.get_cache_key(anonymous_request, view=None)
        assert key is not None
        assert "global_task" in key
        assert "global" in key

    def test_returns_fixed_key_for_authenticated_request(self, authenticated_request):
        """Authenticated requests also get a fixed global cache key."""
        throttle = GlobalTaskThrottle()
        key = throttle.get_cache_key(authenticated_request, view=None)
        assert key is not None
        assert "global_task" in key
        assert "global" in key

    def test_key_is_same_for_any_request(
        self, anonymous_request, authenticated_request
    ):
        """The cache key is identical regardless of authentication status."""
        throttle = GlobalTaskThrottle()
        anon_key = throttle.get_cache_key(anonymous_request, view=None)
        auth_key = throttle.get_cache_key(authenticated_request, view=None)
        assert anon_key == auth_key


class TestFailOpenBehavior:
    """Throttle classes catch Redis ConnectionError and TimeoutError, returning True."""

    @pytest.mark.django_db
    def test_anon_throttle_allows_request_on_connection_error(self, anonymous_request):
        """GlobalAnonThrottle returns True when Redis raises ConnectionError."""
        throttle = GlobalAnonThrottle()
        with patch.object(throttle, "cache", new_callable=MagicMock) as mock_cache:
            mock_cache.get.side_effect = ConnectionError("Redis unavailable")
            result = throttle.allow_request(anonymous_request, view=None)
        assert result is True

    @pytest.mark.django_db
    def test_anon_throttle_allows_request_on_timeout_error(self, anonymous_request):
        """GlobalAnonThrottle returns True when Redis raises TimeoutError."""
        throttle = GlobalAnonThrottle()
        with patch.object(throttle, "cache", new_callable=MagicMock) as mock_cache:
            mock_cache.get.side_effect = TimeoutError("Redis timeout")
            result = throttle.allow_request(anonymous_request, view=None)
        assert result is True

    @pytest.mark.django_db
    def test_authenticated_throttle_allows_request_on_connection_error(
        self, authenticated_request
    ):
        """GlobalAuthenticatedThrottle returns True when Redis raises ConnectionError."""
        throttle = GlobalAuthenticatedThrottle()
        with patch.object(throttle, "cache", new_callable=MagicMock) as mock_cache:
            mock_cache.get.side_effect = ConnectionError("Redis unavailable")
            result = throttle.allow_request(authenticated_request, view=None)
        assert result is True

    @pytest.mark.django_db
    def test_authenticated_throttle_allows_request_on_timeout_error(
        self, authenticated_request
    ):
        """GlobalAuthenticatedThrottle returns True when Redis raises TimeoutError."""
        throttle = GlobalAuthenticatedThrottle()
        with patch.object(throttle, "cache", new_callable=MagicMock) as mock_cache:
            mock_cache.get.side_effect = TimeoutError("Redis timeout")
            result = throttle.allow_request(authenticated_request, view=None)
        assert result is True

    @pytest.mark.django_db
    def test_task_throttle_allows_request_on_connection_error(self, anonymous_request):
        """GlobalTaskThrottle returns True when Redis raises ConnectionError."""
        throttle = GlobalTaskThrottle()
        with patch.object(throttle, "cache", new_callable=MagicMock) as mock_cache:
            mock_cache.get.side_effect = ConnectionError("Redis unavailable")
            result = throttle.allow_request(anonymous_request, view=None)
        assert result is True

    @pytest.mark.django_db
    def test_task_throttle_allows_request_on_timeout_error(self, anonymous_request):
        """GlobalTaskThrottle returns True when Redis raises TimeoutError."""
        throttle = GlobalTaskThrottle()
        with patch.object(throttle, "cache", new_callable=MagicMock) as mock_cache:
            mock_cache.get.side_effect = TimeoutError("Redis timeout")
            result = throttle.allow_request(anonymous_request, view=None)
        assert result is True


class TestThrottleScopes:
    """Throttle classes use the correct scope names."""

    def test_anon_throttle_scope(self):
        """GlobalAnonThrottle uses 'global_anon' scope."""
        throttle = GlobalAnonThrottle()
        assert throttle.scope == "global_anon"

    def test_authenticated_throttle_scope(self):
        """GlobalAuthenticatedThrottle uses 'global_authenticated' scope."""
        throttle = GlobalAuthenticatedThrottle()
        assert throttle.scope == "global_authenticated"

    def test_task_throttle_scope(self):
        """GlobalTaskThrottle uses 'global_task' scope."""
        throttle = GlobalTaskThrottle()
        assert throttle.scope == "global_task"
