"""JSON:API contract tests for Plugin configuration endpoints.

Tests the Plugin JSON:API contract:
- Endpoint: /api/v1/plugins (list), /api/v1/plugins/{id} (detail/update)
- Resource type: plugins
- ID: external_id (16-char string)
- Attributes: name, description, settings, settings_schema
- Media type: application/vnd.api+json
- Pagination: page[number], page[size] with links and meta
- Errors: JSON:API errors array with status, code, detail
"""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from smplfrm.models import Plugin

MOCK_REGISTRY = []


def _setup_registry():
    """Set up a mock plugin registry with a plugin that has secret fields."""
    from smplfrm.plugins.base import BasePlugin

    class FakePlugin(BasePlugin):
        def __init__(self):
            super().__init__(name="fake", description="Fake plugin")

        def get_settings_schema(self):
            return [
                {"key": "api_key", "label": "API Key", "type": "password"},
                {"key": "endpoint", "label": "Endpoint", "type": "text"},
            ]

    class NoSecretsPlugin(BasePlugin):
        def __init__(self):
            super().__init__(name="nosecrets", description="No secrets plugin")

        def get_settings_schema(self):
            return [
                {"key": "color", "label": "Color", "type": "text"},
            ]

    MOCK_REGISTRY.clear()
    MOCK_REGISTRY.append(FakePlugin)
    MOCK_REGISTRY.append(NoSecretsPlugin)
    return FakePlugin, NoSecretsPlugin


class TestPluginListJsonApi(TestCase):
    """Test plugin list endpoint JSON:API contract."""

    def setUp(self):
        self.client = APIClient()
        _setup_registry()
        self.plugin1 = Plugin.objects.create(
            name="fake",
            description="Fake plugin",
            settings={"api_key": "secret123", "endpoint": "https://api.example.com"},
        )
        self.plugin2 = Plugin.objects.create(
            name="nosecrets",
            description="No secrets plugin",
            settings={"color": "blue"},
        )

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    def test_list_returns_jsonapi_media_type(self):
        """Response Content-Type must be application/vnd.api+json."""
        response = self.client.get("/api/v1/plugins")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/vnd.api+json")

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    def test_list_has_top_level_data_array(self):
        """List response must have top-level 'data' as an array."""
        response = self.client.get("/api/v1/plugins")
        data = response.json()

        self.assertIn("data", data)
        self.assertIsInstance(data["data"], list)

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    def test_list_resources_have_type_and_id(self):
        """Each resource must have type and id fields."""
        response = self.client.get("/api/v1/plugins")
        data = response.json()

        for resource in data["data"]:
            self.assertIn("type", resource)
            self.assertIn("id", resource)
            self.assertEqual(resource["type"], "plugins")
            self.assertIsInstance(resource["id"], str)
            self.assertEqual(len(resource["id"]), 16)

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    def test_list_resources_have_attributes(self):
        """Each resource must have attributes with expected fields."""
        response = self.client.get("/api/v1/plugins")
        data = response.json()

        for resource in data["data"]:
            self.assertIn("attributes", resource)
            attrs = resource["attributes"]
            self.assertIn("name", attrs)
            self.assertIn("description", attrs)
            self.assertIn("settings", attrs)
            self.assertIn("settings_schema", attrs)

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    def test_list_has_pagination_links(self):
        """List response must have pagination links."""
        response = self.client.get("/api/v1/plugins")
        data = response.json()

        self.assertIn("links", data)
        links = data["links"]
        self.assertIn("first", links)
        self.assertIn("last", links)

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    def test_list_has_pagination_meta(self):
        """List response must have pagination meta."""
        response = self.client.get("/api/v1/plugins")
        data = response.json()

        self.assertIn("meta", data)
        meta = data["meta"]
        self.assertIn("pagination", meta)
        self.assertIn("count", meta["pagination"])

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    def test_list_secret_fields_masked(self):
        """Secret fields (type=password) must be masked with ******."""
        response = self.client.get("/api/v1/plugins")
        data = response.json()

        fake_resource = next(
            r for r in data["data"] if r["attributes"]["name"] == "fake"
        )
        self.assertEqual(fake_resource["attributes"]["settings"]["api_key"], "******")
        self.assertEqual(
            fake_resource["attributes"]["settings"]["endpoint"],
            "https://api.example.com",
        )

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    def test_list_page_number_pagination(self):
        """Pagination uses page[number] query parameter."""
        # Create more plugins to test pagination
        for i in range(10):
            Plugin.objects.create(
                name=f"plugin{i}",
                description=f"Plugin {i}",
                settings={},
            )

        response = self.client.get("/api/v1/plugins?page[number]=2")
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("links", data)
        self.assertIn("prev", data["links"])


class TestPluginDetailJsonApi(TestCase):
    """Test plugin detail endpoint JSON:API contract."""

    def setUp(self):
        self.client = APIClient()
        _setup_registry()
        self.plugin = Plugin.objects.create(
            name="fake",
            description="Fake plugin",
            settings={"api_key": "secret123", "endpoint": "https://api.example.com"},
        )

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    def test_detail_returns_jsonapi_media_type(self):
        """Response Content-Type must be application/vnd.api+json."""
        response = self.client.get(f"/api/v1/plugins/{self.plugin.external_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/vnd.api+json")

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    def test_detail_has_top_level_data_object(self):
        """Detail response must have top-level 'data' as an object."""
        response = self.client.get(f"/api/v1/plugins/{self.plugin.external_id}")
        data = response.json()

        self.assertIn("data", data)
        self.assertIsInstance(data["data"], dict)

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    def test_detail_resource_has_correct_type_and_id(self):
        """Resource must have correct type and id."""
        response = self.client.get(f"/api/v1/plugins/{self.plugin.external_id}")
        data = response.json()

        self.assertEqual(data["data"]["type"], "plugins")
        self.assertEqual(data["data"]["id"], self.plugin.external_id)

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    def test_detail_secret_fields_masked(self):
        """Secret fields must be masked in detail response."""
        response = self.client.get(f"/api/v1/plugins/{self.plugin.external_id}")
        data = response.json()

        attrs = data["data"]["attributes"]
        self.assertEqual(attrs["settings"]["api_key"], "******")
        self.assertEqual(attrs["settings"]["endpoint"], "https://api.example.com")

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    def test_detail_includes_settings_schema(self):
        """Detail response must include settings_schema."""
        response = self.client.get(f"/api/v1/plugins/{self.plugin.external_id}")
        data = response.json()

        schema = data["data"]["attributes"]["settings_schema"]
        self.assertIsInstance(schema, list)
        self.assertEqual(len(schema), 2)
        self.assertEqual(schema[0]["key"], "api_key")
        self.assertEqual(schema[0]["type"], "password")

    def test_detail_not_found_returns_403(self):
        """Non-existent plugin returns 403 to prevent enumeration attacks."""
        response = self.client.get("/api/v1/plugins/nonexistent12345")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestPluginUpdateJsonApi(TestCase):
    """Test plugin update endpoint JSON:API contract."""

    def setUp(self):
        self.client = APIClient()
        _setup_registry()
        self.plugin = Plugin.objects.create(
            name="fake",
            description="Fake plugin",
            settings={
                "api_key": "original-secret",
                "endpoint": "https://old.example.com",
            },
        )

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    @patch("smplfrm.views.api.v1.plugins.PLUGIN_REGISTRY", MOCK_REGISTRY)
    def test_update_requires_jsonapi_content_type(self):
        """PUT request must use application/vnd.api+json content type."""
        update_data = {
            "data": {
                "type": "plugins",
                "id": self.plugin.external_id,
                "attributes": {
                    "settings": {
                        "api_key": "new-secret",
                        "endpoint": "https://new.example.com",
                    },
                },
            }
        }

        response = self.client.put(
            f"/api/v1/plugins/{self.plugin.external_id}",
            update_data,
            content_type="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    @patch("smplfrm.views.api.v1.plugins.PLUGIN_REGISTRY", MOCK_REGISTRY)
    def test_update_with_wrong_content_type_rejected(self):
        """PUT with application/json should be rejected."""
        update_data = {"settings": {"endpoint": "https://new.example.com"}}

        response = self.client.put(
            f"/api/v1/plugins/{self.plugin.external_id}",
            update_data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    @patch("smplfrm.views.api.v1.plugins.PLUGIN_REGISTRY", MOCK_REGISTRY)
    def test_update_persists_new_secret(self):
        """Submitting a new secret value persists it to the database."""
        update_data = {
            "data": {
                "type": "plugins",
                "id": self.plugin.external_id,
                "attributes": {
                    "settings": {
                        "api_key": "brand-new-secret",
                        "endpoint": "https://new.example.com",
                    },
                },
            }
        }

        response = self.client.put(
            f"/api/v1/plugins/{self.plugin.external_id}",
            update_data,
            content_type="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Response should mask the secret
        data = response.json()
        self.assertEqual(data["data"]["attributes"]["settings"]["api_key"], "******")

        # Database should have the real value
        self.plugin.refresh_from_db()
        self.assertEqual(self.plugin.settings["api_key"], "brand-new-secret")
        self.assertEqual(self.plugin.settings["endpoint"], "https://new.example.com")

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    @patch("smplfrm.views.api.v1.plugins.PLUGIN_REGISTRY", MOCK_REGISTRY)
    def test_update_with_masked_placeholder_retains_original(self):
        """Submitting '******' for a secret retains the stored value."""
        update_data = {
            "data": {
                "type": "plugins",
                "id": self.plugin.external_id,
                "attributes": {
                    "settings": {
                        "api_key": "******",
                        "endpoint": "https://changed.example.com",
                    },
                },
            }
        }

        response = self.client.put(
            f"/api/v1/plugins/{self.plugin.external_id}",
            update_data,
            content_type="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Database should retain original secret
        self.plugin.refresh_from_db()
        self.assertEqual(self.plugin.settings["api_key"], "original-secret")
        self.assertEqual(
            self.plugin.settings["endpoint"], "https://changed.example.com"
        )

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    @patch("smplfrm.views.api.v1.plugins.PLUGIN_REGISTRY", MOCK_REGISTRY)
    def test_update_returns_jsonapi_response(self):
        """PUT response must be valid JSON:API document."""
        update_data = {
            "data": {
                "type": "plugins",
                "id": self.plugin.external_id,
                "attributes": {
                    "settings": {
                        "api_key": "******",
                        "endpoint": "https://example.com",
                    },
                },
            }
        }

        response = self.client.put(
            f"/api/v1/plugins/{self.plugin.external_id}",
            update_data,
            content_type="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/vnd.api+json")

        data = response.json()
        self.assertIn("data", data)
        self.assertEqual(data["data"]["type"], "plugins")
        self.assertEqual(data["data"]["id"], self.plugin.external_id)


class TestPluginForbiddenOperations(TestCase):
    """Test that forbidden operations return proper JSON:API errors."""

    def setUp(self):
        self.client = APIClient()
        _setup_registry()
        self.plugin = Plugin.objects.create(
            name="fake",
            description="Fake plugin",
            settings={},
        )

    def test_create_forbidden(self):
        """POST to create plugin should be forbidden."""
        create_data = {
            "data": {
                "type": "plugins",
                "attributes": {
                    "name": "newplugin",
                    "description": "New plugin",
                    "settings": {},
                },
            }
        }

        response = self.client.post(
            "/api/v1/plugins",
            create_data,
            content_type="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_forbidden(self):
        """PATCH for partial update should be forbidden."""
        patch_data = {
            "data": {
                "type": "plugins",
                "id": self.plugin.external_id,
                "attributes": {
                    "settings": {"color": "red"},
                },
            }
        }

        response = self.client.patch(
            f"/api/v1/plugins/{self.plugin.external_id}",
            patch_data,
            content_type="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_forbidden(self):
        """DELETE should be forbidden."""
        response = self.client.delete(f"/api/v1/plugins/{self.plugin.external_id}")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestPluginNoSecretsPlugin(TestCase):
    """Test plugins without secret fields."""

    def setUp(self):
        self.client = APIClient()
        _setup_registry()
        self.plugin = Plugin.objects.create(
            name="nosecrets",
            description="No secrets plugin",
            settings={"color": "blue"},
        )

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    def test_no_secrets_plugin_settings_unmodified(self):
        """Plugins without secret fields have settings returned as-is."""
        response = self.client.get(f"/api/v1/plugins/{self.plugin.external_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["data"]["attributes"]["settings"]["color"], "blue")
