"""Tests for shared JSON:API pagination.

The shared paginator uses server-controlled page[number] with fixed page size.
"""

from django.test import TestCase, RequestFactory
from rest_framework.request import Request

from smplfrm.jsonapi.pagination import JsonApiPagination


class JsonApiPaginationTest(TestCase):
    """Test shared JSON:API paginator."""

    def setUp(self):
        self.factory = RequestFactory()
        self.paginator = JsonApiPagination()

    def test_page_size_is_five(self):
        """Page size is hardcoded to 5."""
        self.assertEqual(self.paginator.page_size, 5)

    def test_page_number_parameter_accepted(self):
        """Paginator accepts page[number] parameter."""
        request = self.factory.get("/api/v1/test", {"page[number]": "2"})
        drf_request = Request(request)

        # Create a queryset to paginate
        items = list(range(20))
        paginated = self.paginator.paginate_queryset(items, drf_request)

        # Should return items 5-9 (second page of 5)
        self.assertEqual(len(paginated), 5)
        self.assertEqual(paginated, [5, 6, 7, 8, 9])

    def test_first_page_returns_correct_items(self):
        """First page returns first 5 items."""
        request = self.factory.get("/api/v1/test", {"page[number]": "1"})
        drf_request = Request(request)

        items = list(range(20))
        paginated = self.paginator.paginate_queryset(items, drf_request)

        self.assertEqual(len(paginated), 5)
        self.assertEqual(paginated, [0, 1, 2, 3, 4])

    def test_pagination_links_included(self):
        """Paginated response includes links for first/last/next/prev."""
        request = self.factory.get("/api/v1/test", {"page[number]": "2"})
        drf_request = Request(request)

        items = list(range(20))
        paginated = self.paginator.paginate_queryset(items, drf_request)
        response_data = self.paginator.get_paginated_response(paginated)

        self.assertIn("links", response_data.data)
        links = response_data.data["links"]

        self.assertIn("first", links)
        self.assertIn("last", links)
        self.assertIn("next", links)
        self.assertIn("prev", links)

    def test_pagination_meta_included(self):
        """Paginated response includes meta.pagination with counts."""
        request = self.factory.get("/api/v1/test", {"page[number]": "2"})
        drf_request = Request(request)

        items = list(range(20))
        paginated = self.paginator.paginate_queryset(items, drf_request)
        response_data = self.paginator.get_paginated_response(paginated)

        self.assertIn("meta", response_data.data)
        self.assertIn("pagination", response_data.data["meta"])

        pagination = response_data.data["meta"]["pagination"]
        self.assertEqual(pagination["page"], 2)
        self.assertEqual(pagination["pages"], 4)  # 20 items / 5 per page
        self.assertEqual(pagination["count"], 20)

    def test_last_page_has_remaining_items(self):
        """Last page returns remaining items even if less than page size."""
        request = self.factory.get("/api/v1/test", {"page[number]": "3"})
        drf_request = Request(request)

        items = list(range(12))  # 12 items = 3 pages of 5, 5, 2
        paginated = self.paginator.paginate_queryset(items, drf_request)

        self.assertEqual(len(paginated), 2)
        self.assertEqual(paginated, [10, 11])

    def test_page_size_parameter_rejected(self):
        """page[size] parameter should be rejected or ignored.

        Note: This test documents expected behavior. The actual rejection
        will be implemented via StrictQueryMixin in views, not the paginator itself.
        The paginator simply doesn't use page[size] even if present.
        """
        request = self.factory.get("/api/v1/test", {"page[size]": "10"})
        drf_request = Request(request)

        items = list(range(20))
        paginated = self.paginator.paginate_queryset(items, drf_request)

        # Should still return 5 items, ignoring page[size]
        self.assertEqual(len(paginated), 5)

    def test_default_first_page_when_no_page_param(self):
        """When no page parameter provided, returns first page."""
        request = self.factory.get("/api/v1/test")
        drf_request = Request(request)

        items = list(range(20))
        paginated = self.paginator.paginate_queryset(items, drf_request)

        self.assertEqual(len(paginated), 5)
        self.assertEqual(paginated, [0, 1, 2, 3, 4])

    def test_empty_queryset_returns_empty_page(self):
        """Empty queryset returns empty page without error."""
        request = self.factory.get("/api/v1/test")
        drf_request = Request(request)

        items = []
        paginated = self.paginator.paginate_queryset(items, drf_request)

        self.assertEqual(len(paginated), 0)
