"""Shared JSON:API pagination for smplFrm.

Provides server-controlled page[number] pagination with fixed page size.
Client cannot control page size per API standards.
"""

from rest_framework_json_api.pagination import JsonApiPageNumberPagination


class JsonApiPagination(JsonApiPageNumberPagination):
    """Server-controlled JSON:API pagination.

    - Fixed page size: 5 items per page
    - Accepts only page[number] parameter
    - Emits links (first/last/next/prev) and meta.pagination
    - Client cannot override page size
    """

    page_size = 5
    max_page_size = 5  # Prevent client override
    page_size_query_param = None  # Disable page[size] parameter
