"""Route discovery for contract validation.

Discovers all routes under /api/v1/ after Django and plugin initialization.
"""

from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver


def discover_routes() -> set[tuple[str, str]]:
    """Discover all /api/v1/ routes from Django URL configuration.

    Returns:
        Set of (method, pattern) tuples for all discovered routes.
        Pattern uses Django angle-bracket syntax: /api/v1/images/<str:external_id>

    Example:
        {
            ('GET', '/api/v1/images'),
            ('GET', '/api/v1/images/<str:external_id>'),
            ('PUT', '/api/v1/configs/<str:external_id>'),
            ...
        }
    """
    resolver = get_resolver()
    routes = set()

    def extract_routes(url_patterns, prefix=""):
        """Recursively extract routes from URL patterns."""
        for pattern in url_patterns:
            if isinstance(pattern, URLResolver):
                # Nested URL include - recurse
                new_prefix = prefix + str(pattern.pattern)
                extract_routes(pattern.url_patterns, new_prefix)
            elif isinstance(pattern, URLPattern):
                # Actual endpoint
                full_pattern = prefix + str(pattern.pattern)

                # Only include /api/v1/ routes
                if not full_pattern.startswith("api/v1/"):
                    continue

                # Skip format suffix routes (e.g., .json, .xml)
                if r"\.(?P<format>" in full_pattern:
                    continue

                # Normalize pattern format
                full_pattern = normalize_pattern(full_pattern)

                # Get allowed methods from the view
                methods = _extract_methods(pattern)

                for method in methods:
                    routes.add((method, full_pattern))

    extract_routes(resolver.url_patterns)
    return routes


def _extract_methods(pattern: URLPattern) -> set[str]:
    """Extract HTTP methods from a URL pattern's view.

    Args:
        pattern: Django URLPattern

    Returns:
        Set of HTTP method names (e.g., {'GET', 'POST', 'PUT'})
    """
    view = pattern.callback
    methods = set()

    # Handle ViewSet-based views (DRF)
    if hasattr(view, "cls"):
        viewset_class = view.cls
        actions = getattr(view, "actions", {})

        # Map actions to methods
        for http_method, action_name in actions.items():
            methods.add(http_method.upper())

        # Check for extra actions (like @action decorated methods)
        if hasattr(viewset_class, "get_extra_actions"):
            for action in viewset_class.get_extra_actions():
                if "mapping" in action.kwargs:
                    for method in action.kwargs["mapping"].keys():
                        methods.add(method.upper())

    # Handle function-based views or APIView
    elif hasattr(view, "view_class"):
        view_class = view.view_class
        # Check allowed methods
        if hasattr(view_class, "http_method_names"):
            # Get actual implemented methods
            for method in view_class.http_method_names:
                method_upper = method.upper()
                if method_upper in {
                    "GET",
                    "POST",
                    "PUT",
                    "PATCH",
                    "DELETE",
                    "HEAD",
                    "OPTIONS",
                    "TRACE",
                }:
                    # Check if method is actually implemented
                    if hasattr(view_class, method.lower()):
                        methods.add(method_upper)

    # Handle plain function views
    elif callable(view):
        # Default to GET for simple function views
        methods.add("GET")

    # Filter out HTTP metadata methods
    methods.discard("HEAD")
    methods.discard("OPTIONS")
    methods.discard("TRACE")

    return methods if methods else {"GET"}  # Default to GET if no methods found


def normalize_pattern(pattern: str) -> str:
    """Normalize Django URL pattern to consistent format.

    Converts various Django URL pattern syntaxes to angle-bracket format:
    - ^api/v1/images -> /api/v1/images
    - (?P<name>[^/]+) -> <str:name>
    - (?P<pk>[0-9]+) -> <int:pk>

    Args:
        pattern: Raw Django URL pattern string

    Returns:
        Normalized pattern string with leading slash
    """
    import re

    # Remove all ^ anchors (can appear at multiple positions due to URL includes)
    pattern = re.sub(r"\^", "", pattern)

    # Remove trailing $ anchor and optional trailing slash
    pattern = re.sub(r"/?\$$", "", pattern)

    # Convert named regex groups to angle-bracket syntax
    # (?P<external_id>[^/.]+) -> <str:external_id>
    pattern = re.sub(r"\(\?P<(\w+)>\[.*?\]\+?\)", r"<str:\1>", pattern)

    # (?P<pk>[0-9]+) -> <int:pk>
    pattern = re.sub(r"\(\?P<(\w+)>\[0-9\]\+\)", r"<int:\1>", pattern)

    # Ensure leading slash
    if not pattern.startswith("/"):
        pattern = "/" + pattern

    return pattern


def format_route_diff(
    discovered: set[tuple[str, str]], manifest: set[tuple[str, str]]
) -> str:
    """Format human-readable diff between discovered and manifest routes.

    Args:
        discovered: Set of discovered (method, pattern) tuples
        manifest: Set of manifest (method, pattern) tuples

    Returns:
        Formatted string showing missing and extra routes
    """
    missing = sorted(discovered - manifest)
    extra = sorted(manifest - discovered)

    lines = []

    if missing:
        lines.append("\n❌ UNCLASSIFIED ROUTES (in code, missing from manifest):")
        for method, pattern in missing:
            lines.append(f"   {method:6} {pattern}")

    if extra:
        lines.append("\n❌ STALE MANIFEST ENTRIES (in manifest, not found in code):")
        for method, pattern in extra:
            lines.append(f"   {method:6} {pattern}")

    if not missing and not extra:
        lines.append("\n✓ All routes match manifest")

    return "\n".join(lines)
