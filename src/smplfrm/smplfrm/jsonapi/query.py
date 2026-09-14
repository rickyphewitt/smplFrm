"""Strict query parameter validation for JSON:API endpoints.

Per API standards, endpoints must reject:
- include, fields[...], sort (unless explicitly allowed via sort profiles)
- Unknown parameters
- Raw ORM lookups
- Legacy filter spellings after migration

Validation runs BEFORE any domain/queryset access.

Filter parameters (filter[field]) are allowed through by default per JSON:API spec.
Individual routes should validate filter field names in their view/serializer logic.
Protocol-exempt actions (e.g., binary image delivery) should be listed in exempt_actions.
"""

from rest_framework.request import Request

from smplfrm.jsonapi.exceptions import InvalidQueryParameterError

# Parameters that are conditionally forbidden per JSON:API profile
CONDITIONALLY_FORBIDDEN_PARAMS = frozenset({"sort"})

# Parameters that are always forbidden per JSON:API profile
ALWAYS_FORBIDDEN_PARAMS = frozenset({"include"})

# Patterns that indicate forbidden field sparse fieldsets
FORBIDDEN_PREFIXES = ("fields[",)


class StrictQueryMixin:
    """Mixin for views requiring strict query parameter validation.

    Add this mixin to a ViewSet or APIView and define:
    - allowed_query_params: set of allowed parameter names (default: empty)
    - allowed_sort_profiles: set of allowed curated sort profile keys (default: empty)
    - allowed_filters: set of allowed filter field names (default: empty, meaning all allowed)
    - exempt_actions: set of action names exempt from validation (default: empty)

    Query validation runs in initial() before any action method.

    Sort profiles are curated ordering strategies, not raw model fields.
    When sort is in allowed_query_params and allowed_sort_profiles is non-empty,
    the sort parameter value must be exactly one profile key from the allowed set.
    Direction prefixes (-), commas, and raw field names are rejected.

    Filter validation:
    - If allowed_filters is empty (default), all filter[field] params pass through
    - If allowed_filters is non-empty, only listed fields are accepted

    Actions in exempt_actions skip all query validation (e.g., non-JSON:API actions).
    """

    # Subclasses can override these sets
    allowed_query_params: set[str] = set()
    allowed_sort_profiles: set[str] = set()
    allowed_filters: set[str] = set()
    exempt_actions: set[str] = set()

    def initial(self, request: Request, *args, **kwargs) -> None:
        """Validate query parameters before processing the request."""
        # Skip validation for exempt actions
        action_name = getattr(self, "action", None)
        if action_name not in self.exempt_actions:
            self._validate_query_params(request)
        super().initial(request, *args, **kwargs)

    def _validate_query_params(self, request: Request) -> None:
        """Check all query parameters against allowlist and sort profile rules.

        Raises InvalidQueryParameterError for any violations.
        """
        query_params = request.query_params

        for param in query_params:
            # Handle filter[] parameters per JSON:API spec
            if param.startswith("filter[") and param.endswith("]"):
                # Extract field name from filter[field]
                field_name = param[7:-1]  # Remove "filter[" prefix and "]" suffix
                # If allowed_filters is defined, validate against it
                if self.allowed_filters and field_name not in self.allowed_filters:
                    raise InvalidQueryParameterError(param)
                continue

            # Check always-forbidden params
            if param in ALWAYS_FORBIDDEN_PARAMS:
                raise InvalidQueryParameterError(param)

            # Check forbidden prefixes (e.g., fields[...])
            for prefix in FORBIDDEN_PREFIXES:
                if param.startswith(prefix):
                    raise InvalidQueryParameterError(param)

            # Handle sort parameter specially
            if param == "sort":
                if param not in self.allowed_query_params:
                    # Sort not allowed at all for this route
                    raise InvalidQueryParameterError(param)
                # Sort is allowed - validate the profile value
                self._validate_sort_profile(request)
                continue

            # Check if param is in the general allowlist
            if param not in self.allowed_query_params:
                raise InvalidQueryParameterError(param)

    def _validate_sort_profile(self, request: Request) -> None:
        """Validate sort parameter value against allowed profiles.

        Enforces:
        - Single value (no repeated sort params)
        - Non-blank
        - No commas (no multi-field sorting)
        - No direction prefixes (-, +)
        - Value must be in allowed_sort_profiles set
        """
        sort_values = request.query_params.getlist("sort")

        # Reject duplicate sort parameters
        if len(sort_values) > 1:
            raise InvalidQueryParameterError("sort")

        sort_value = sort_values[0] if sort_values else ""

        # Reject blank values
        if not sort_value or not sort_value.strip():
            raise InvalidQueryParameterError("sort")

        # Reject comma-separated values
        if "," in sort_value:
            raise InvalidQueryParameterError("sort")

        # Reject direction prefixes
        if sort_value.startswith("-") or sort_value.startswith("+"):
            raise InvalidQueryParameterError("sort")

        # Reject values not in the allowed profile set
        if sort_value not in self.allowed_sort_profiles:
            raise InvalidQueryParameterError("sort")
