from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from smplfrm.models import Image, ImageTag, Tag

URI = "/api/v1/tags"


class TagsViewTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.frame = Tag.objects.create(value="frame", display_value="Frame")
        self.beach = Tag.objects.create(value="beach", display_value="Beach")

    def make_image(self, name):
        return Image.objects.create(
            name=name, file_name=name, file_path=f"/library/{name}"
        )

    def assert_error(self, response, status_code, code):
        self.assertEqual(response.status_code, status_code)
        errors = response.json()["errors"]
        self.assertEqual(errors[0]["status"], str(status_code))
        self.assertEqual(errors[0]["code"], code)


class TestTagsList(TagsViewTestBase):
    def test_list_returns_tags_ordered_by_value(self):
        response = self.client.get(URI)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(
            [d["id"] for d in data], [self.beach.external_id, self.frame.external_id]
        )
        self.assertEqual(data[0]["type"], "tags")

    def test_list_resource_shape(self):
        response = self.client.get(URI, {"filter[value]": "frame"})

        (resource,) = response.json()["data"]
        self.assertEqual(
            set(resource["attributes"]),
            {"value", "display_value", "usage_count", "created", "updated"},
        )
        self.assertEqual(resource["attributes"]["value"], "frame")
        self.assertEqual(resource["attributes"]["display_value"], "Frame")
        self.assertNotIn("relationships", resource)

    def test_list_is_paginated(self):
        body = self.client.get(URI).json()

        self.assertIn("links", body)
        self.assertIn("pagination", body["meta"])

    def test_list_hides_deleted_tags(self):
        self.beach.deleted = True
        self.beach.save()

        data = self.client.get(URI).json()["data"]

        self.assertEqual([d["id"] for d in data], [self.frame.external_id])

    def test_usage_count_ignores_deleted_images(self):
        first = self.make_image("1.jpg")
        second = self.make_image("2.jpg")
        ImageTag.objects.create(image=first, tag=self.frame)
        ImageTag.objects.create(image=second, tag=self.frame)

        detail_uri = f"{URI}/{self.frame.external_id}"
        self.assertEqual(
            self.client.get(detail_uri).json()["data"]["attributes"]["usage_count"], 2
        )

        second.deleted = True
        second.save()

        listed = {
            d["id"]: d["attributes"]["usage_count"]
            for d in self.client.get(URI).json()["data"]
        }
        self.assertEqual(listed[self.frame.external_id], 1)
        self.assertEqual(listed[self.beach.external_id], 0)
        self.assertEqual(
            self.client.get(detail_uri).json()["data"]["attributes"]["usage_count"], 1
        )

    def test_query_count_does_not_grow_with_tag_count(self):
        image = self.make_image("1.jpg")
        ImageTag.objects.create(image=image, tag=self.frame)
        with CaptureQueriesContext(connection) as few:
            self.client.get(URI)

        for value in ("a", "b", "c"):
            tag = Tag.objects.create(value=value, display_value=value)
            ImageTag.objects.create(image=image, tag=tag)
        with CaptureQueriesContext(connection) as more:
            self.client.get(URI)

        self.assertEqual(len(more), len(few))


class TestTagsFilter(TagsViewTestBase):
    def test_filter_by_value(self):
        data = self.client.get(URI, {"filter[value]": "frame"}).json()["data"]

        self.assertEqual([d["id"] for d in data], [self.frame.external_id])

    def test_filter_by_value_is_canonicalized(self):
        data = self.client.get(URI, {"filter[value]": " FRAME "}).json()["data"]

        self.assertEqual([d["id"] for d in data], [self.frame.external_id])

    def test_filter_without_match_is_empty(self):
        response = self.client.get(URI, {"filter[value]": "nothing"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"], [])


class TestTagsQueryPolicy(TagsViewTestBase):
    def test_unapproved_query_parameters_are_rejected(self):
        for params in (
            {"sort": "-usage_count"},
            {"sort": "value"},
            {"include": "image_tags"},
            {"fields[tags]": "value"},
            {"filter[usage_count]": "1"},
            {"filter[display_value]": "Frame"},
            {"value": "frame"},
        ):
            with self.subTest(params=params):
                self.assert_error(
                    self.client.get(URI, params),
                    status.HTTP_400_BAD_REQUEST,
                    "invalid_query_parameter",
                )

    def test_page_number_is_accepted(self):
        response = self.client.get(URI, {"page[number]": "1"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestTagsDetail(TagsViewTestBase):
    def test_detail(self):
        response = self.client.get(f"{URI}/{self.frame.external_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resource = response.json()["data"]
        self.assertEqual(resource["type"], "tags")
        self.assertEqual(resource["id"], self.frame.external_id)
        self.assertEqual(resource["attributes"]["usage_count"], 0)

    def test_unknown_id_returns_403(self):
        response = self.client.get(f"{URI}/unknownTagId0001")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("errors", response.json())

    def test_deleted_tag_returns_403(self):
        self.frame.deleted = True
        self.frame.save()

        response = self.client.get(f"{URI}/{self.frame.external_id}")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestTagsMutationsNotAllowed(TagsViewTestBase):
    def body(self):
        return {"data": {"type": "tags", "attributes": {"value": "new"}}}

    def test_collection_post_returns_405(self):
        response = self.client.post(
            URI, self.body(), content_type="application/vnd.api+json"
        )

        self.assert_error(
            response, status.HTTP_405_METHOD_NOT_ALLOWED, "method_not_allowed"
        )
        self.assertFalse(Tag.objects.filter(value="new").exists())

    def test_detail_mutations_return_405(self):
        detail = f"{URI}/{self.frame.external_id}"
        for method in ("put", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    detail, self.body(), content_type="application/vnd.api+json"
                )
                self.assert_error(
                    response, status.HTTP_405_METHOD_NOT_ALLOWED, "method_not_allowed"
                )

        self.frame.refresh_from_db()
        self.assertFalse(self.frame.deleted)
        self.assertEqual(self.frame.value, "frame")
