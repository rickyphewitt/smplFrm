from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from smplfrm.models import Plugin
from smplfrm.services.plugin_service import PluginService


class TestPluginService(TestCase):

    def setUp(self):
        self.service = PluginService()

    def test_sync_plugins_creates_rows(self):
        Plugin.objects.all().delete()
        self.service.sync_plugins()
        self.assertTrue(Plugin.objects.filter(name="weather").exists())
        self.assertTrue(Plugin.objects.filter(name="spotify").exists())

    def test_sync_plugins_idempotent(self):
        Plugin.objects.all().delete()
        self.service.sync_plugins()
        count = Plugin.objects.count()
        self.service.sync_plugins()
        self.assertEqual(Plugin.objects.count(), count)

    def test_list(self):
        Plugin.objects.all().delete()
        Plugin.objects.create(name="alpha", settings={})
        Plugin.objects.create(name="beta", settings={})
        names = [p.name for p in self.service.list()]
        self.assertEqual(names, ["alpha", "beta"])

    def test_read_by_name(self):
        Plugin.objects.all().delete()
        Plugin.objects.create(name="weather", settings={"coords": "1,2"})
        p = self.service.read_by_name("weather")
        self.assertEqual(p.settings["coords"], "1,2")

    def test_update(self):
        Plugin.objects.all().delete()
        p = Plugin.objects.create(name="weather", settings={})
        p.settings = {"coords": "3,4"}
        self.service.update(p)
        p.refresh_from_db()
        self.assertEqual(p.settings["coords"], "3,4")


class TestPluginAPI(TestCase):

    def setUp(self):
        self.client = APIClient()
        Plugin.objects.all().delete()
        self.plugin = Plugin.objects.create(
            name="weather",
            description="Weather data",
            settings={"coords": "63.17,-147.46"},
        )
        self.url = f"/api/v1/plugins/{self.plugin.external_id}"

    def test_list_plugins(self):
        response = self.client.get("/api/v1/plugins")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "weather")

    def test_retrieve_plugin(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "weather")
        self.assertEqual(response.data["settings"]["coords"], "63.17,-147.46")

    def test_update_plugin_settings(self):
        response = self.client.put(
            self.url,
            {
                "name": "weather",
                "description": "Weather data",
                "settings": {"coords": "40.71,-74.00"},
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.plugin.refresh_from_db()
        self.assertEqual(self.plugin.settings["coords"], "40.71,-74.00")

    def test_update_plugin_name_ignored(self):
        """PUT with different name silently ignores it."""
        response = self.client.put(
            self.url,
            {
                "name": "renamed",
                "description": "Weather data",
                "settings": {"coords": "40.71,-74.00"},
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.plugin.refresh_from_db()
        self.assertEqual(self.plugin.name, "weather")
        self.assertEqual(self.plugin.settings["coords"], "40.71,-74.00")

    def test_update_plugin_description_ignored(self):
        """PUT with different description silently ignores it."""
        response = self.client.put(
            self.url,
            {
                "name": "weather",
                "description": "Changed",
                "settings": {"coords": "40.71,-74.00"},
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.plugin.refresh_from_db()
        self.assertEqual(self.plugin.description, "Weather data")
        self.assertEqual(self.plugin.settings["coords"], "40.71,-74.00")

    def test_create_plugin_forbidden(self):
        response = self.client.post("/api/v1/plugins", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_plugin_forbidden(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
