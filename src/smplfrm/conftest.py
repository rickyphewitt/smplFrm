"""Root conftest for smplfrm test suite.

Clears the Django cache before each test to prevent throttle state
from leaking between tests.
"""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache():
    """Reset cache before each test so throttle counters don't leak."""
    cache.clear()
    yield
    cache.clear()
