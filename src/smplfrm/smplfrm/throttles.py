"""Custom throttle classes for global-bucket rate limiting.

Provides three throttle classes that use a shared global counter (rather than
per-IP) to protect the system from aggregate request flooding:

- GlobalAnonThrottle: limits anonymous (unauthenticated) requests
- GlobalAuthenticatedThrottle: limits authenticated requests
- GlobalTaskThrottle: limits task creation requests regardless of auth status

All classes fail open when Redis is unavailable, logging a warning instead of
blocking requests.
"""

import logging

from rest_framework.throttling import SimpleRateThrottle

logger = logging.getLogger(__name__)

# Default rates used when REST_FRAMEWORK settings are not yet configured.
_DEFAULT_RATES = {
    "global_anon": "60/minute",
    "global_authenticated": "120/minute",
    "global_task": "10/minute",
}


class _FailOpenThrottleMixin:
    """Mixin that provides fail-open behavior and default rate fallback.

    Catches ConnectionError and TimeoutError from Redis during throttle checks
    and allows the request through, logging a warning. Also provides a default
    rate when the scope is not configured in REST_FRAMEWORK settings.
    """

    def get_rate(self):
        """Return the rate from current settings, falling back to built-in defaults.

        Reads directly from api_settings to respect override_settings in tests,
        since SimpleRateThrottle.THROTTLE_RATES is a class attribute set once
        at import time and is not updated when settings change.
        """
        from rest_framework.settings import api_settings

        try:
            rates = api_settings.DEFAULT_THROTTLE_RATES or {}
            return rates[self.scope]
        except (KeyError, TypeError):
            return _DEFAULT_RATES.get(self.scope)

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except (ConnectionError, TimeoutError):
            logger.warning(
                "Redis unavailable during %s throttle check, allowing request",
                self.scope,
            )
            return True


class GlobalAnonThrottle(_FailOpenThrottleMixin, SimpleRateThrottle):
    """Global bucket throttle for anonymous requests.

    Returns a fixed cache key for anonymous requests so all unauthenticated
    clients share a single rate limit counter. Authenticated requests are
    skipped (returns None) since they are handled by GlobalAuthenticatedThrottle.
    """

    scope = "global_anon"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": "global"}


class GlobalAuthenticatedThrottle(_FailOpenThrottleMixin, SimpleRateThrottle):
    """Global bucket throttle for authenticated requests.

    Returns a fixed cache key for authenticated requests so all authenticated
    clients share a single rate limit counter. Anonymous requests are skipped
    (returns None) since they are handled by GlobalAnonThrottle.
    """

    scope = "global_authenticated"

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": "global"}


class GlobalTaskThrottle(_FailOpenThrottleMixin, SimpleRateThrottle):
    """Global bucket throttle for task creation endpoint.

    Always returns a fixed cache key regardless of authentication status,
    applying a shared rate limit to all task creation requests.
    """

    scope = "global_task"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": "global"}
