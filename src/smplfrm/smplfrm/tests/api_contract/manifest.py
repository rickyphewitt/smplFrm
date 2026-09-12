"""API Contract Manifest.

This module defines the authoritative classification of every /api/v1/ route.

Every route must be explicitly classified. Adding a new endpoint requires
adding an entry here, or contract validation will fail.

Per ai/api-standards.md, the project implements JSON:API 1.1 with a documented
PUT deviation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Protocol(Enum):
    """Protocol classification for API routes."""

    JSON_API = "json_api"
    BINARY = "binary"
    OAUTH_EXEMPT = "oauth_exempt"
    REDIRECT_EXEMPT = "redirect_exempt"


@dataclass(frozen=True)
class RouteContract:
    """Contract definition for a single route-method pair.

    Attributes:
        method: HTTP method (GET, PUT, POST, DELETE, PATCH)
        pattern: URL pattern (e.g., "/api/v1/images")
        protocol: Protocol classification
        resource_type: JSON:API resource type (required for json_api protocol)
        allowed_query_params: Set of permitted query parameter names
        exemption_reason: Required explanation for non-json_api protocols
        notes: Optional implementation notes
    """

    method: str
    pattern: str
    protocol: Protocol
    resource_type: Optional[str]
    allowed_query_params: set[str]
    exemption_reason: Optional[str]
    notes: Optional[str] = None

    def __post_init__(self):
        """Validate contract consistency."""
        if self.protocol == Protocol.JSON_API and not self.resource_type:
            raise ValueError(
                f"JSON:API route {self.method} {self.pattern} must specify resource_type"
            )
        if self.protocol != Protocol.JSON_API and not self.exemption_reason:
            raise ValueError(
                f"Exempt route {self.method} {self.pattern} must specify exemption_reason"
            )


# The authoritative manifest
CONTRACT_MANIFEST: list[RouteContract] = [
    # -------------------------------------------------------------------------
    # Core Images API
    # -------------------------------------------------------------------------
    RouteContract(
        method="GET",
        pattern="/api/v1/images",
        protocol=Protocol.JSON_API,
        resource_type="images",
        allowed_query_params={"page[number]"},
        exemption_reason=None,
        notes="Paginated list of non-deleted images",
    ),
    RouteContract(
        method="POST",
        pattern="/api/v1/images",
        protocol=Protocol.JSON_API,
        resource_type="images",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - creation not supported",
    ),
    RouteContract(
        method="GET",
        pattern="/api/v1/images/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="images",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Image detail; returns 403 for nonexistent to prevent enumeration",
    ),
    RouteContract(
        method="PUT",
        pattern="/api/v1/images/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="images",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - update not supported",
    ),
    RouteContract(
        method="PATCH",
        pattern="/api/v1/images/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="images",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - PATCH not supported per profile",
    ),
    RouteContract(
        method="DELETE",
        pattern="/api/v1/images/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="images",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - deletion not supported",
    ),
    RouteContract(
        method="GET",
        pattern="/api/v1/images/next",
        protocol=Protocol.JSON_API,
        resource_type="images",
        allowed_query_params={"width", "height"},
        exemption_reason=None,
        notes="Next image for display cycle; width/height are custom display parameters",
    ),
    RouteContract(
        method="GET",
        pattern="/api/v1/images/<str:external_id>/display",
        protocol=Protocol.BINARY,
        resource_type=None,
        allowed_query_params={"width", "height"},
        exemption_reason="Binary JPEG delivery with server-side resize",
        notes="Returns image/jpeg with optional dimensions; cached",
    ),
    # -------------------------------------------------------------------------
    # Image Metadata API
    # -------------------------------------------------------------------------
    RouteContract(
        method="GET",
        pattern="/api/v1/images_metadata",
        protocol=Protocol.JSON_API,
        resource_type="images_metadata",
        allowed_query_params={"page[number]"},
        exemption_reason=None,
        notes="Paginated list of image metadata",
    ),
    RouteContract(
        method="POST",
        pattern="/api/v1/images_metadata",
        protocol=Protocol.JSON_API,
        resource_type="images_metadata",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - creation not supported",
    ),
    RouteContract(
        method="GET",
        pattern="/api/v1/images_metadata/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="images_metadata",
        allowed_query_params=set(),
        exemption_reason=None,
    ),
    RouteContract(
        method="PUT",
        pattern="/api/v1/images_metadata/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="images_metadata",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - update not supported",
    ),
    RouteContract(
        method="PATCH",
        pattern="/api/v1/images_metadata/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="images_metadata",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - PATCH not supported per profile",
    ),
    RouteContract(
        method="DELETE",
        pattern="/api/v1/images_metadata/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="images_metadata",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - deletion not supported",
    ),
    # -------------------------------------------------------------------------
    # Config API
    # -------------------------------------------------------------------------
    RouteContract(
        method="GET",
        pattern="/api/v1/configs",
        protocol=Protocol.JSON_API,
        resource_type="configs",
        allowed_query_params={"page[number]"},
        exemption_reason=None,
    ),
    RouteContract(
        method="POST",
        pattern="/api/v1/configs",
        protocol=Protocol.JSON_API,
        resource_type="configs",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - creation not supported",
    ),
    RouteContract(
        method="GET",
        pattern="/api/v1/configs/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="configs",
        allowed_query_params=set(),
        exemption_reason=None,
    ),
    RouteContract(
        method="PUT",
        pattern="/api/v1/configs/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="configs",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Complete PUT with secret masking",
    ),
    RouteContract(
        method="PATCH",
        pattern="/api/v1/configs/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="configs",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - PATCH not supported per profile",
    ),
    RouteContract(
        method="DELETE",
        pattern="/api/v1/configs/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="configs",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - deletion not supported",
    ),
    # -------------------------------------------------------------------------
    # Task API
    # -------------------------------------------------------------------------
    RouteContract(
        method="GET",
        pattern="/api/v1/tasks",
        protocol=Protocol.JSON_API,
        resource_type="tasks",
        allowed_query_params={"page[number]"},
        exemption_reason=None,
    ),
    RouteContract(
        method="POST",
        pattern="/api/v1/tasks",
        protocol=Protocol.JSON_API,
        resource_type="tasks",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - creation not supported",
    ),
    RouteContract(
        method="GET",
        pattern="/api/v1/tasks/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="tasks",
        allowed_query_params=set(),
        exemption_reason=None,
    ),
    RouteContract(
        method="PUT",
        pattern="/api/v1/tasks/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="tasks",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - update not supported",
    ),
    RouteContract(
        method="PATCH",
        pattern="/api/v1/tasks/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="tasks",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - PATCH not supported per profile",
    ),
    RouteContract(
        method="DELETE",
        pattern="/api/v1/tasks/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="tasks",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - deletion not supported",
    ),
    # -------------------------------------------------------------------------
    # Plugin API
    # -------------------------------------------------------------------------
    RouteContract(
        method="GET",
        pattern="/api/v1/plugins",
        protocol=Protocol.JSON_API,
        resource_type="plugins",
        allowed_query_params={"page[number]"},
        exemption_reason=None,
    ),
    RouteContract(
        method="POST",
        pattern="/api/v1/plugins",
        protocol=Protocol.JSON_API,
        resource_type="plugins",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - creation not supported",
    ),
    RouteContract(
        method="GET",
        pattern="/api/v1/plugins/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="plugins",
        allowed_query_params=set(),
        exemption_reason=None,
    ),
    RouteContract(
        method="PUT",
        pattern="/api/v1/plugins/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="plugins",
        allowed_query_params=set(),
        exemption_reason=None,
    ),
    RouteContract(
        method="PATCH",
        pattern="/api/v1/plugins/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="plugins",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - PATCH not supported per profile",
    ),
    RouteContract(
        method="DELETE",
        pattern="/api/v1/plugins/<str:external_id>",
        protocol=Protocol.JSON_API,
        resource_type="plugins",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Returns 405 - deletion not supported",
    ),
    # -------------------------------------------------------------------------
    # Weather Plugin
    # -------------------------------------------------------------------------
    RouteContract(
        method="GET",
        pattern="/api/v1/plugins/weather/current",
        protocol=Protocol.JSON_API,
        resource_type="weather",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Singleton resource with id='current'",
    ),
    # -------------------------------------------------------------------------
    # Spotify Plugin
    # -------------------------------------------------------------------------
    RouteContract(
        method="GET",
        pattern="/api/v1/plugins/spotify/status",
        protocol=Protocol.JSON_API,
        resource_type="spotify_status",
        allowed_query_params=set(),
        exemption_reason=None,
        notes="Current playback status; requires auth",
    ),
    RouteContract(
        method="GET",
        pattern="/api/v1/plugins/spotify/auth",
        protocol=Protocol.OAUTH_EXEMPT,
        resource_type=None,
        allowed_query_params=set(),
        exemption_reason="Native JSON auth initiation response with auth_url",
        notes="Returns {auth_url, success} for OAuth flow initiation",
    ),
    RouteContract(
        method="GET",
        pattern="/api/v1/plugins/spotify/callback",
        protocol=Protocol.REDIRECT_EXEMPT,
        resource_type=None,
        allowed_query_params={"code", "state"},
        exemption_reason="OAuth callback with redirect and HTML error pages",
        notes="OAuth code exchange; redirects on success, HTML on error",
    ),
]


def get_manifest_routes() -> set[tuple[str, str]]:
    """Return set of (method, pattern) tuples from manifest.

    Used for comparing against discovered routes.
    """
    return {(contract.method, contract.pattern) for contract in CONTRACT_MANIFEST}


def get_contract(method: str, pattern: str) -> RouteContract | None:
    """Look up contract for a specific route.

    Args:
        method: HTTP method
        pattern: URL pattern

    Returns:
        RouteContract if found, None otherwise
    """
    for contract in CONTRACT_MANIFEST:
        if contract.method == method and contract.pattern == pattern:
            return contract
    return None
