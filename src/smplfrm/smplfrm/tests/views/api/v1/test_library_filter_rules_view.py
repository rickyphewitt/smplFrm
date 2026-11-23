from unittest import mock

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from smplfrm.models import LibraryFilter, LibraryFilterRule, Tag, Task
from smplfrm.services.library_filter.rule_handlers import RULE_TYPE_HANDLERS
from smplfrm.views.serializers.v1.library_filter_rules import RULE_SERIALIZERS

URI = "/api/v1/library_filter_rules"
JSONAPI = "application/vnd.api+json"
TAG_RULE_TYPE = "tag_library_filter_rules"


def ref(resource_type, resource_id):
    return {"data": {"type": resource_type, "id": resource_id}}


class LibraryFilterRulesViewTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.library_filter = LibraryFilter.objects.create(name="frame")
        self.frame = Tag.objects.create(value="frame", display_value="Frame")
        self.beach = Tag.objects.create(value="beach", display_value="Beach")

    def relationships(self, library_filter=None, tag=None):
        relationships = {}
        if library_filter is not None:
            relationships["library_filter"] = ref("library_filters", library_filter)
        if tag is not None:
            relationships["tag"] = ref("tags", tag)
        return relationships

    def body(self, relationships, resource_type=TAG_RULE_TYPE, resource_id=None):
        data = {"type": resource_type, "relationships": relationships}
        if resource_id:
            data["id"] = resource_id
        return {"data": data}

    def post(self, relationships, resource_type=TAG_RULE_TYPE):
        return self.client.post(
            URI, self.body(relationships, resource_type), content_type=JSONAPI
        )

    def post_tag_rule(self, library_filter=None, tag=None):
        return self.post(
            self.relationships(
                (library_filter or self.library_filter).external_id,
                (tag or self.frame).external_id,
            )
        )

    def make_rule(self, tag=None, library_filter=None):
        return LibraryFilterRule.objects.create(
            library_filter=library_filter or self.library_filter, tag=tag or self.frame
        )

    def put(self, rule, relationships, resource_type=TAG_RULE_TYPE):
        return self.client.put(
            f"{URI}/{rule.external_id}",
            self.body(relationships, resource_type, rule.external_id),
            content_type=JSONAPI,
        )

    def assert_error(self, response, status_code, code):
        self.assertEqual(response.status_code, status_code, response.content)
        self.assertEqual(response.json()["errors"][0]["code"], code)


class TestCreate(LibraryFilterRulesViewTestBase):
    def test_create_tag_rule(self):
        response = self.post_tag_rule()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        resource = response.json()["data"]
        self.assertEqual(resource["type"], TAG_RULE_TYPE)
        self.assertEqual(set(resource["attributes"]), {"created", "updated"})
        self.assertEqual(
            resource["relationships"]["library_filter"]["data"],
            {"type": "library_filters", "id": self.library_filter.external_id},
        )
        self.assertEqual(
            resource["relationships"]["tag"]["data"],
            {"type": "tags", "id": self.frame.external_id},
        )

    def test_detail_has_the_same_shape(self):
        created = self.post_tag_rule().json()["data"]

        response = self.client.get(f"{URI}/{created['id']}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fetched = response.json()["data"]
        self.assertEqual(fetched["type"], created["type"])
        self.assertEqual(fetched["relationships"], created["relationships"])
        self.assertEqual(set(fetched["attributes"]), {"created", "updated"})

    def test_missing_tag_is_rejected(self):
        for relationships in (
            self.relationships(self.library_filter.external_id),
            {
                **self.relationships(self.library_filter.external_id),
                "tag": {"data": None},
            },
        ):
            with self.subTest(relationships=relationships):
                self.assert_error(
                    self.post(relationships),
                    status.HTTP_400_BAD_REQUEST,
                    "tag_required",
                )

    def test_unknown_or_deleted_tag_is_rejected(self):
        gone = Tag.objects.create(value="gone", deleted=True)
        for tag_id in ("unknownTagId0001", gone.external_id):
            with self.subTest(tag_id=tag_id):
                self.assert_error(
                    self.post(
                        self.relationships(self.library_filter.external_id, tag_id)
                    ),
                    status.HTTP_400_BAD_REQUEST,
                    "tag_not_found",
                )

    def test_missing_library_filter_is_rejected(self):
        self.assert_error(
            self.post(self.relationships(tag=self.frame.external_id)),
            status.HTTP_400_BAD_REQUEST,
            "library_filter_required",
        )

    def test_unknown_or_deleted_library_filter_returns_403(self):
        gone = LibraryFilter.objects.create(name="gone", deleted=True)
        for filter_id in ("unknownFilter001", gone.external_id):
            with self.subTest(filter_id=filter_id):
                response = self.post(
                    self.relationships(filter_id, self.frame.external_id)
                )
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(LibraryFilterRule.objects.exists())

    def test_unknown_rule_type_is_rejected(self):
        self.assert_error(
            self.post(
                self.relationships(
                    self.library_filter.external_id, self.frame.external_id
                ),
                resource_type="date_library_filter_rules",
            ),
            status.HTTP_400_BAD_REQUEST,
            "unknown_rule_type",
        )

    def test_duplicate_rule_is_rejected(self):
        self.post_tag_rule()

        self.assert_error(
            self.post_tag_rule(), status.HTTP_400_BAD_REQUEST, "duplicate_rule"
        )

    def test_tag_can_be_added_again_after_its_rule_is_deleted(self):
        created = self.post_tag_rule().json()["data"]
        self.client.delete(f"{URI}/{created['id']}")

        self.assertEqual(self.post_tag_rule().status_code, status.HTTP_201_CREATED)


class TestUpdate(LibraryFilterRulesViewTestBase):
    def tag_relationships(self, tag, library_filter=None):
        return self.relationships(
            (library_filter or self.library_filter).external_id, tag.external_id
        )

    def test_change_to_an_unused_tag(self):
        rule = self.make_rule()

        response = self.put(rule, self.tag_relationships(self.beach))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["data"]["relationships"]["tag"]["data"]["id"],
            self.beach.external_id,
        )
        self.assertEqual(LibraryFilterRule.objects.get(pk=rule.pk).tag, self.beach)

    def test_keeping_its_own_tag(self):
        rule = self.make_rule()

        response = self.put(rule, self.tag_relationships(self.frame))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_tag_used_by_another_rule_is_rejected(self):
        rule = self.make_rule()
        self.make_rule(tag=self.beach)

        self.assert_error(
            self.put(rule, self.tag_relationships(self.beach)),
            status.HTTP_400_BAD_REQUEST,
            "duplicate_rule",
        )

    def test_tag_checks_apply_on_update(self):
        rule = self.make_rule()

        self.assert_error(
            self.put(rule, self.relationships(self.library_filter.external_id)),
            status.HTTP_400_BAD_REQUEST,
            "tag_required",
        )
        self.assert_error(
            self.put(
                rule,
                self.relationships(self.library_filter.external_id, "unknownTagId0001"),
            ),
            status.HTTP_400_BAD_REQUEST,
            "tag_not_found",
        )

    def test_type_change_is_rejected(self):
        rule = self.make_rule()

        self.assert_error(
            self.put(
                rule,
                self.tag_relationships(self.frame),
                resource_type="date_library_filter_rules",
            ),
            status.HTTP_400_BAD_REQUEST,
            "type_mismatch",
        )

    def test_moving_to_another_filter_is_rejected(self):
        rule = self.make_rule()
        other = LibraryFilter.objects.create(name="other")

        self.assert_error(
            self.put(rule, self.tag_relationships(self.frame, library_filter=other)),
            status.HTTP_400_BAD_REQUEST,
            "library_filter_immutable",
        )
        self.assertEqual(
            LibraryFilterRule.objects.get(pk=rule.pk).library_filter,
            self.library_filter,
        )

    def test_missing_library_filter_is_rejected(self):
        rule = self.make_rule()

        self.assert_error(
            self.put(rule, self.relationships(tag=self.frame.external_id)),
            status.HTTP_400_BAD_REQUEST,
            "library_filter_required",
        )

    def test_unknown_id_returns_403(self):
        response = self.client.put(
            f"{URI}/unknownRuleId001",
            self.body(
                self.tag_relationships(self.frame), resource_id="unknownRuleId001"
            ),
            content_type=JSONAPI,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_returns_405(self):
        rule = self.make_rule()

        response = self.client.patch(
            f"{URI}/{rule.external_id}",
            self.body(self.tag_relationships(self.frame), resource_id=rule.external_id),
            content_type=JSONAPI,
        )

        self.assert_error(
            response, status.HTTP_405_METHOD_NOT_ALLOWED, "method_not_allowed"
        )


class TestDelete(LibraryFilterRulesViewTestBase):
    def test_delete_is_soft_and_hides_the_rule(self):
        rule = self.make_rule()

        response = self.client.delete(f"{URI}/{rule.external_id}")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(LibraryFilterRule.objects.get(pk=rule.pk).deleted)
        self.assertEqual(
            self.client.get(f"{URI}/{rule.external_id}").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_deleting_the_last_rule_deactivates_the_active_filter(self):
        rule = self.make_rule()
        self.library_filter.is_active = True
        self.library_filter.save()

        self.client.delete(f"{URI}/{rule.external_id}")

        self.assertFalse(LibraryFilter.objects.get(pk=self.library_filter.pk).is_active)

    def test_deleting_one_of_several_rules_keeps_the_filter_active(self):
        rule = self.make_rule()
        self.make_rule(tag=self.beach)
        self.library_filter.is_active = True
        self.library_filter.save()

        self.client.delete(f"{URI}/{rule.external_id}")

        self.assertTrue(LibraryFilter.objects.get(pk=self.library_filter.pk).is_active)

    def test_delete_unknown_id_returns_403(self):
        response = self.client.delete(f"{URI}/unknownRuleId001")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestList(LibraryFilterRulesViewTestBase):
    def ids(self, params=None):
        response = self.client.get(URI, params or {})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        return [d["id"] for d in response.json()["data"]]

    def test_list_hides_deleted_rules(self):
        live = self.make_rule()
        gone = self.make_rule(tag=self.beach)
        gone.deleted = True
        gone.save()

        self.assertEqual(self.ids(), [live.external_id])

    def test_filter_by_library_filter(self):
        mine = self.make_rule()
        other = LibraryFilter.objects.create(name="other")
        self.make_rule(library_filter=other)

        self.assertEqual(
            self.ids({"filter[library_filter]": self.library_filter.external_id}),
            [mine.external_id],
        )

    def test_filter_by_rule_type(self):
        rule = self.make_rule()

        self.assertEqual(self.ids({"filter[rule_type]": "tag"}), [rule.external_id])
        self.assertEqual(self.ids({"filter[rule_type]": "date"}), [])

    def test_unapproved_query_parameters_are_rejected(self):
        for params in (
            {"include": "library_filter"},
            {"sort": "created"},
            {"filter[tag]": "x"},
        ):
            with self.subTest(params=params):
                self.assert_error(
                    self.client.get(URI, params),
                    status.HTTP_400_BAD_REQUEST,
                    "invalid_query_parameter",
                )

    def test_list_relationships_do_not_add_queries_per_rule(self):
        self.make_rule()
        with CaptureQueriesContext(connection) as few:
            self.client.get(URI)

        for value in ("a", "b", "c"):
            self.make_rule(tag=Tag.objects.create(value=value))
        with CaptureQueriesContext(connection) as more:
            self.client.get(URI)

        self.assertEqual(len(more), len(few))


class TestNoTaskDispatch(LibraryFilterRulesViewTestBase):
    def test_no_task_dispatch(self):
        tasks_before = Task.objects.count()
        with mock.patch("smplfrm.celery.app.send_task") as send_task:
            created = self.post_tag_rule().json()["data"]
            rule = LibraryFilterRule.objects.get(external_id=created["id"])
            self.put(
                rule,
                self.relationships(
                    self.library_filter.external_id, self.beach.external_id
                ),
            )
            self.client.delete(f"{URI}/{rule.external_id}")

        send_task.assert_not_called()
        self.assertEqual(Task.objects.count(), tasks_before)


class TestRuleSerializerRegistry(TestCase):
    def test_every_rule_type_has_a_serializer(self):
        self.assertEqual(set(RULE_SERIALIZERS), set(RULE_TYPE_HANDLERS))
