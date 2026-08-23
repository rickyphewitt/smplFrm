"""Strict query parameter validation for JSON:API endpoints.

Per api-standards.md, endpoints must reject:
- include, fields[...], sort
- Unknown parameters
- Raw ORM lookups
- Legacy filter spellings after migration

Validation runs BEFORE any domain/queryset access.
"""

from rest_framework.request import Request

from smplfrm.jsonapi.exceptions import InvalidQueryParameterError

# Parameters that are always forbidden per JSON:API profile
FORBIDDEN_PARAMS = frozenset({"include", "sort"})

# Patterns that indicate forbidden field sparse fieldsets
FORBIDDEN_PREFIXES = ("fields[",)


class StrictQueryMixin:
    """Mixin for views requiring strict query parameter validation.

    Add this mixin to a ViewSet or APIView and define:
    - allowed_query_params: set of allowed parameter names (default: empty)

    Query validation runs in initial() before any action method.
    """

    # Subclasses can override this set
    allowed_query_params: set[str] = set()

    def initial(self, request: Request, *args, **kwargs) -> None:
        """Validate query parameters before processing the request."""
        self._validate_query_params(request)
        super().initial(request, *args, **kwargs)

    def _validate_query_params(self, request: Request) -> None:
        """Check all query parameters against allowlist.

        Raises InvalidQueryParameterError for any violations.
        """
        query_params = request.query_params

        for param in query_params:
            # Check explicitly forbidden params
            if param in FORBIDDEN_PARAMS:
                raise InvalidQueryParameterError(param)

            # Check forbidden prefixes (e.g., fields[...])
            for prefix in FORBIDDEN_PREFIXES:
                if param.startswith(prefix):
                    raise InvalidQueryParameterError(param)

            # Check if param is in the allowlist
            if param not in self.allowed_query_params:
                raise InvalidQueryParameterError(param)
