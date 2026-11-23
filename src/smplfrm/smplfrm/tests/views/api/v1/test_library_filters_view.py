from unittest import mock

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from smplfrm.models import LibraryFilter, LibraryFilterRule, Tag, Task

URI = "/api/v1/library_filters"
JSONAPI = "application/vnd.api+json"


class LibraryFiltersViewTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def make_filter(self, name, is_active=False, rules=0, description=""):
        library_filter = LibraryFilter.objects.create(
            name=name, is_active=is_active, description=description
        )
        for i in range(rules):
            tag = Tag.objects.create(value=f"{name}-{i}")
            LibraryFilterRule.objects.create(library_filter=library_filter, tag=tag)
        return library_filter

    def body(self, attributes, resource_id=None, relationships=None):
        data = {"type": "library_filters", "attributes": attributes}
        if resource_id:
            data["id"] = resource_id
        if relationships:
            data["relationships"] = relationships
        return {"data": data}

    def post(self, attributes, relationships=None):
        return self.client.post(
            URI,
            self.body(attributes, relationships=relationships),
            content_type=JSONAPI,
        )

    def put(self, library_filter, attributes, relationships=None):
        return self.client.put(
            f"{URI}/{library_filter.external_id}",
            self.body(attributes, library_filter.external_id, relationships),
            content_type=JSONAPI,
        )

    def assert_error(self, response, status_code, code):
        self.assertEqual(response.status_code, status_code, response.content)
        self.assertEqual(response.json()["errors"][0]["code"], code)

    def stored(self, library_filter):
        return LibraryFilter.objects.get(pk=library_filter.pk)


class TestCreate(LibraryFiltersViewTestBase):
    def test_create_returns_201_with_defaults(self):
        response = self.post({"name": "Frame"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        resource = response.json()["data"]
        self.assertEqual(resource["type"], "library_filters")
        self.assertEqual(len(resource["id"]), 16)
        self.assertEqual(
            resource["attributes"],
            {
                "name": "Frame",
                "description": "",
                "is_active": False,
                "created": resource["attributes"]["created"],
                "updated": resource["attributes"]["updated"],
            },
        )
        self.assertEqual(resource["relationships"]["rules"]["data"], [])

    def test_create_requires_name(self):
        self.assert_error(
            self.post({"description": "x"}),
            status.HTTP_400_BAD_REQUEST,
            "validation_error",
        )

    def test_create_duplicate_name_is_rejected(self):
        self.make_filter("Frame")

        self.assert_error(
            self.post({"name": "Frame"}), status.HTTP_400_BAD_REQUEST, "unique_name"
        )

    def test_create_active_is_rejected_without_rules(self):
        self.assert_error(
            self.post({"name": "Frame", "is_active": True}),
            status.HTTP_400_BAD_REQUEST,
            "rule_required",
        )
        self.assertFalse(LibraryFilter.objects.exists())

    def test_create_ignores_rules_relationship(self):
        other = self.make_filter("other", rules=1)
        rule = LibraryFilterRule.objects.get(library_filter=other)

        response = self.post(
            {"name": "Frame"},
            relationships={
                "rules": {
                    "data": [
                        {"type": "tag_library_filter_rules", "id": rule.external_id}
                    ]
                }
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["data"]["relationships"]["rules"]["data"], [])
        self.assertEqual(
            LibraryFilterRule.objects.get(pk=rule.pk).library_filter, other
        )


class TestUpdate(LibraryFiltersViewTestBase):
    def test_activation_deactivates_the_previous_filter(self):
        previous = self.make_filter("previous", is_active=True, rules=1)
        library_filter = self.make_filter("frame", rules=1)

        response = self.put(library_filter, {"name": "frame", "is_active": True})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["data"]["attributes"]["is_active"])
        self.assertFalse(self.stored(previous).is_active)

    def test_activation_without_rules_is_rejected(self):
        library_filter = self.make_filter("frame")

        self.assert_error(
            self.put(library_filter, {"name": "frame", "is_active": True}),
            status.HTTP_400_BAD_REQUEST,
            "rule_required",
        )
        self.assertFalse(self.stored(library_filter).is_active)

    def test_omitted_fields_are_reset(self):
        library_filter = self.make_filter(
            "frame", is_active=True, rules=1, description="x"
        )

        response = self.put(library_filter, {"name": "frame"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        attributes = response.json()["data"]["attributes"]
        self.assertEqual(attributes["description"], "")
        self.assertFalse(attributes["is_active"])

    def test_put_requires_name(self):
        library_filter = self.make_filter("frame")

        self.assert_error(
            self.put(library_filter, {"description": "x"}),
            status.HTTP_400_BAD_REQUEST,
            "validation_error",
        )

    def test_rename_to_taken_name_is_rejected(self):
        self.make_filter("taken")
        library_filter = self.make_filter("frame")

        self.assert_error(
            self.put(library_filter, {"name": "taken"}),
            status.HTTP_400_BAD_REQUEST,
            "unique_name",
        )

    def test_put_ignores_rules_relationship(self):
        library_filter = self.make_filter("frame", rules=1)
        rule = LibraryFilterRule.objects.get(library_filter=library_filter)

        response = self.put(
            library_filter, {"name": "frame"}, relationships={"rules": {"data": []}}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["data"]["relationships"]["rules"]["data"],
            [{"type": "tag_library_filter_rules", "id": rule.external_id}],
        )

    def test_put_unknown_id_returns_403(self):
        response = self.client.put(
            f"{URI}/unknownFilter001",
            self.body({"name": "x"}, "unknownFilter001"),
            content_type=JSONAPI,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_returns_405(self):
        library_filter = self.make_filter("frame")

        response = self.client.patch(
            f"{URI}/{library_filter.external_id}",
            self.body({"name": "x"}, library_filter.external_id),
            content_type=JSONAPI,
        )

        self.assert_error(
            response, status.HTTP_405_METHOD_NOT_ALLOWED, "method_not_allowed"
        )


class TestRead(LibraryFiltersViewTestBase):
    def test_detail_lists_live_rule_identifiers(self):
        library_filter = self.make_filter("frame", rules=3)
        rules = list(
            LibraryFilterRule.objects.filter(library_filter=library_filter).order_by(
                "id"
            )
        )
        rules[1].deleted = True
        rules[1].save()

        response = self.client.get(f"{URI}/{library_filter.external_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertNotIn("included", body)
        self.assertEqual(
            body["data"]["relationships"]["rules"]["data"],
            [
                {"type": "tag_library_filter_rules", "id": rules[0].external_id},
                {"type": "tag_library_filter_rules", "id": rules[2].external_id},
            ],
        )

    def test_unknown_or_deleted_id_returns_403(self):
        gone = self.make_filter("gone")
        gone.deleted = True
        gone.save()

        for filter_id in ("unknownFilter001", gone.external_id):
            with self.subTest(filter_id=filter_id):
                response = self.client.get(f"{URI}/{filter_id}")
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_is_ordered_by_name_and_hides_deleted(self):
        self.make_filter("b")
        self.make_filter("a")
        gone = self.make_filter("c")
        gone.deleted = True
        gone.save()

        data = self.client.get(URI).json()["data"]

        self.assertEqual([d["attributes"]["name"] for d in data], ["a", "b"])

    def test_list_filters_on_is_active(self):
        self.make_filter("active", is_active=True, rules=1)
        self.make_filter("idle")

        active = self.client.get(URI, {"filter[is_active]": "true"}).json()["data"]
        idle = self.client.get(URI, {"filter[is_active]": "false"}).json()["data"]

        self.assertEqual([d["attributes"]["name"] for d in active], ["active"])
        self.assertEqual([d["attributes"]["name"] for d in idle], ["idle"])

    def test_invalid_is_active_filter_value_is_rejected(self):
        self.assert_error(
            self.client.get(URI, {"filter[is_active]": "yes"}),
            status.HTTP_400_BAD_REQUEST,
            "invalid_query_parameter",
        )

    def test_unapproved_query_parameters_are_rejected(self):
        for params in (
            {"include": "rules"},
            {"sort": "name"},
            {"filter[name]": "a"},
            {"fields[library_filters]": "name"},
        ):
            with self.subTest(params=params):
                self.assert_error(
                    self.client.get(URI, params),
                    status.HTTP_400_BAD_REQUEST,
                    "invalid_query_parameter",
                )

    def test_list_rule_relationships_do_not_add_queries_per_filter(self):
        self.make_filter("a", rules=2)
        with CaptureQueriesContext(connection) as few:
            self.client.get(URI)

        self.make_filter("b", rules=2)
        self.make_filter("c", rules=2)
        with CaptureQueriesContext(connection) as more:
            self.client.get(URI)

        self.assertEqual(len(more), len(few))


class TestDelete(LibraryFiltersViewTestBase):
    def test_delete_active_filter(self):
        library_filter = self.make_filter("frame", is_active=True, rules=2)

        response = self.client.delete(f"{URI}/{library_filter.external_id}")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        active = self.client.get(URI, {"filter[is_active]": "true"}).json()["data"]
        self.assertEqual(active, [])
        self.assertFalse(
            LibraryFilterRule.objects.filter(
                library_filter=library_filter, deleted=False
            ).exists()
        )
        self.assertEqual(
            self.client.get(f"{URI}/{library_filter.external_id}").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_delete_unknown_id_returns_403(self):
        response = self.client.delete(f"{URI}/unknownFilter001")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestNoTaskDispatch(LibraryFiltersViewTestBase):
    def test_no_task_dispatch(self):
        tasks_before = Task.objects.count()
        with mock.patch("smplfrm.celery.app.send_task") as send_task:
            created = self.post({"name": "frame"}).json()["data"]
            library_filter = LibraryFilter.objects.get(external_id=created["id"])
            self.put(library_filter, {"name": "renamed"})
            self.client.delete(f"{URI}/{library_filter.external_id}")

        send_task.assert_not_called()
        self.assertEqual(Task.objects.count(), tasks_before)
