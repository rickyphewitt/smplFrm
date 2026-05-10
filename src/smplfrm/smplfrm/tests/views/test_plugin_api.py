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


class TestPluginSecretProtection(TestCase):
    """Test that plugin secrets are masked in API responses."""

    def setUp(self):
        self.client = APIClient()
        _setup_registry()
        self.plugin = Plugin.objects.create(
            name="fake",
            description="Fake plugin",
            settings={
                "api_key": "super-secret-value",
                "endpoint": "https://api.example.com",
            },
        )
        self.no_secrets_plugin = Plugin.objects.create(
            name="nosecrets",
            description="No secrets plugin",
            settings={"color": "blue"},
        )

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    def test_secret_fields_masked_in_detail_response(self):
        """Secret fields should be replaced with '******' in GET responses."""
        response = self.client.get(f"/api/v1/plugins/{self.plugin.external_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["settings"]["api_key"], "******")
        self.assertEqual(
            response.data["settings"]["endpoint"], "https://api.example.com"
        )

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    def test_secret_fields_masked_in_list_response(self):
        """Secret fields should be masked in list responses too."""
        response = self.client.get("/api/v1/plugins")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        fake_plugin = next(p for p in results if p["name"] == "fake")
        self.assertEqual(fake_plugin["settings"]["api_key"], "******")
        self.assertEqual(fake_plugin["settings"]["endpoint"], "https://api.example.com")

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    def test_no_secrets_plugin_settings_unmodified(self):
        """Plugins without secret fields should have settings returned as-is."""
        response = self.client.get(
            f"/api/v1/plugins/{self.no_secrets_plugin.external_id}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["settings"]["color"], "blue")

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    @patch("smplfrm.views.api.v1.plugins.PLUGIN_REGISTRY", MOCK_REGISTRY)
    def test_update_with_real_secret_persists_value(self):
        """Submitting a real secret value should persist it to the database."""
        update_data = {
            "settings": {
                "api_key": "new-secret",
                "endpoint": "https://new.example.com",
            },
        }

        response = self.client.put(
            f"/api/v1/plugins/{self.plugin.external_id}",
            update_data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response should mask the secret
        self.assertEqual(response.data["settings"]["api_key"], "******")
        self.assertEqual(
            response.data["settings"]["endpoint"], "https://new.example.com"
        )

        # But the DB should have the real value
        self.plugin.refresh_from_db()
        self.assertEqual(self.plugin.settings["api_key"], "new-secret")

    @patch(
        "smplfrm.views.serializers.v1.plugin_serializer.PLUGIN_REGISTRY", MOCK_REGISTRY
    )
    @patch("smplfrm.views.api.v1.plugins.PLUGIN_REGISTRY", MOCK_REGISTRY)
    def test_update_with_masked_placeholder_retains_original(self):
        """Submitting '******' for a secret field should retain the stored value."""
        update_data = {
            "settings": {
                "api_key": "******",
                "endpoint": "https://changed.example.com",
            },
        }

        response = self.client.put(
            f"/api/v1/plugins/{self.plugin.external_id}",
            update_data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["settings"]["endpoint"], "https://changed.example.com"
        )

        # DB should retain the original secret, not the placeholder
        self.plugin.refresh_from_db()
        self.assertEqual(self.plugin.settings["api_key"], "super-secret-value")
        self.assertEqual(
            self.plugin.settings["endpoint"], "https://changed.example.com"
        )
