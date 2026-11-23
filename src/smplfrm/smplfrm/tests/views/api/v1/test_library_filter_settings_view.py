from unittest import mock

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from smplfrm.models import LibraryFilterSettings, Task

URI = "/api/v1/library_filter_settings"
JSONAPI = "application/vnd.api+json"


class TestLibraryFilterSettingsView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.settings = LibraryFilterSettings.objects.get()
        self.detail = f"{URI}/{self.settings.external_id}"

    def put(self, attributes, resource_id=None):
        body = {
            "data": {
                "type": "library_filter_settings",
                "id": resource_id or self.settings.external_id,
                "attributes": attributes,
            }
        }
        return self.client.put(self.detail, body, content_type=JSONAPI)

    def assert_error(self, response, status_code, code):
        self.assertEqual(response.status_code, status_code)
        self.assertEqual(response.json()["errors"][0]["code"], code)

    def test_list_returns_the_single_disabled_row(self):
        response = self.client.get(URI)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        (resource,) = response.json()["data"]
        self.assertEqual(resource["type"], "library_filter_settings")
        self.assertEqual(resource["id"], self.settings.external_id)
        self.assertFalse(resource["attributes"]["enabled"])
        self.assertEqual(set(resource["attributes"]), {"enabled", "created", "updated"})

    def test_detail(self):
        response = self.client.get(self.detail)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["id"], self.settings.external_id)

    def test_unknown_id_returns_403(self):
        response = self.client.get(f"{URI}/unknownSettings1")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_enables_without_starting_a_task(self):
        tasks_before = Task.objects.count()
        with mock.patch("smplfrm.celery.app.send_task") as send_task:
            response = self.put({"enabled": True})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["data"]["attributes"]["enabled"])
        self.assertTrue(LibraryFilterSettings.objects.get().enabled)
        self.assertEqual(Task.objects.count(), tasks_before)
        send_task.assert_not_called()

    def test_put_can_disable_again(self):
        self.put({"enabled": True})

        response = self.put({"enabled": False})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(LibraryFilterSettings.objects.get().enabled)

    def test_put_without_enabled_is_rejected(self):
        self.assert_error(self.put({}), status.HTTP_400_BAD_REQUEST, "validation_error")

    def test_put_with_non_boolean_is_rejected(self):
        self.assert_error(
            self.put({"enabled": "maybe"}),
            status.HTTP_400_BAD_REQUEST,
            "validation_error",
        )

    def test_put_unknown_id_returns_403(self):
        response = self.client.put(
            f"{URI}/unknownSettings1",
            {
                "data": {
                    "type": "library_filter_settings",
                    "id": "unknownSettings1",
                    "attributes": {"enabled": True},
                }
            },
            content_type=JSONAPI,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(LibraryFilterSettings.objects.get().enabled)

    def test_other_methods_return_405(self):
        body = {"data": {"type": "library_filter_settings", "attributes": {}}}
        for method, uri in (
            ("post", URI),
            ("patch", self.detail),
            ("delete", self.detail),
        ):
            with self.subTest(method=method):
                response = getattr(self.client, method)(uri, body, content_type=JSONAPI)
                self.assert_error(
                    response,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                    "method_not_allowed",
                )
        self.assertEqual(LibraryFilterSettings.objects.count(), 1)

    def test_query_parameters_other_than_page_are_rejected(self):
        for params in ({"filter[enabled]": "true"}, {"sort": "enabled"}, {"x": "1"}):
            with self.subTest(params=params):
                self.assert_error(
                    self.client.get(URI, params),
                    status.HTTP_400_BAD_REQUEST,
                    "invalid_query_parameter",
                )
        self.assertEqual(
            self.client.get(URI, {"page[number]": "1"}).status_code,
            status.HTTP_200_OK,
        )
