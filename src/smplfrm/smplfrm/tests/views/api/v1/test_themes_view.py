"""JSON:API contract tests for the themes endpoint.

Tests the Themes JSON:API contract:
- Endpoint: /api/v1/themes (collection only)
- Resource type: themes
- ID: theme id from the registry (stable string)
- Attributes: label, description
- No stylesheet attribute, no included, no detail route
- Media type: application/vnd.api+json
- Pagination: page[number] with links and meta
- Strict query validation
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from smplfrm.themes import get_all_themes


class TestThemesListJsonApi(TestCase):
    """Test themes list endpoint JSON:API contract."""

    def setUp(self):
        self.client = APIClient()

    def test_list_returns_jsonapi_media_type(self):
        """Response Content-Type must be application/vnd.api+json."""
        response = self.client.get("/api/v1/themes")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/vnd.api+json")

    def test_list_has_top_level_data_array(self):
        """List response must have top-level 'data' as an array."""
        response = self.client.get("/api/v1/themes")
        data = response.json()

        self.assertIn("data", data)
        self.assertIsInstance(data["data"], list)

    def test_list_resources_have_type_and_id(self):
        """Each resource must have type 'themes' and a string id matching the registry."""
        response = self.client.get("/api/v1/themes")
        data = response.json()

        for resource in data["data"]:
            self.assertEqual(resource["type"], "themes")
            self.assertIsInstance(resource["id"], str)

    def test_list_resources_have_label_and_description_attributes(self):
        """Each resource must expose label and description under attributes."""
        response = self.client.get("/api/v1/themes")
        data = response.json()

        for resource in data["data"]:
            attrs = resource["attributes"]
            self.assertIn("label", attrs)
            self.assertIn("description", attrs)

    def test_list_does_not_expose_stylesheet(self):
        """The stylesheet path is server-side detail and must never be serialized."""
        response = self.client.get("/api/v1/themes")
        data = response.json()

        for resource in data["data"]:
            self.assertNotIn("stylesheet", resource["attributes"])

    def test_list_does_not_emit_included(self):
        """No included compound documents."""
        response = self.client.get("/api/v1/themes")
        data = response.json()

        self.assertNotIn("included", data)

    def test_list_has_pagination_links(self):
        """List response must have pagination links."""
        response = self.client.get("/api/v1/themes")
        data = response.json()

        self.assertIn("links", data)
        self.assertIn("first", data["links"])
        self.assertIn("last", data["links"])

    def test_list_has_pagination_meta(self):
        """List response must have pagination meta."""
        response = self.client.get("/api/v1/themes")
        data = response.json()

        self.assertIn("meta", data)
        self.assertIn("pagination", data["meta"])
        self.assertIn("count", data["meta"]["pagination"])

    def test_list_preserves_registry_declaration_order(self):
        """Resources must appear in registry declaration order."""
        response = self.client.get("/api/v1/themes")
        data = response.json()

        expected_ids = [theme.id for theme in get_all_themes()]
        actual_ids = [resource["id"] for resource in data["data"]]
        self.assertEqual(actual_ids, expected_ids[: len(actual_ids)])

    def test_list_contains_classic_theme(self):
        """The classic theme must be present with its registered attributes."""
        response = self.client.get("/api/v1/themes")
        data = response.json()

        classic = next((r for r in data["data"] if r["id"] == "classic"), None)
        self.assertIsNotNone(classic)
        self.assertEqual(classic["attributes"]["label"], "Classic")


class TestThemesStrictQueryValidation(TestCase):
    """Strict query parameter validation on the themes collection."""

    def setUp(self):
        self.client = APIClient()

    def test_include_rejected(self):
        response = self.client.get("/api/v1/themes?include=foo")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fields_rejected(self):
        response = self.client.get("/api/v1/themes?fields[themes]=label")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sort_rejected(self):
        response = self.client.get("/api/v1/themes?sort=label")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_rejected(self):
        response = self.client.get("/api/v1/themes?filter[label]=Classic")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_parameter_rejected(self):
        response = self.client.get("/api/v1/themes?bogus=1")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_page_number_accepted(self):
        response = self.client.get("/api/v1/themes?page[number]=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestThemesMethodRestriction(TestCase):
    """Only GET is routed on the themes collection; no detail route exists."""

    def setUp(self):
        self.client = APIClient()

    def test_post_returns_405(self):
        response = self.client.post(
            "/api/v1/themes",
            {"data": {"type": "themes", "attributes": {}}},
            content_type="application/vnd.api+json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_detail_route_not_routed(self):
        response = self.client.get("/api/v1/themes/classic")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
