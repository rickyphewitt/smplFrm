from unittest import mock

from django.test import TestCase

from smplfrm.models import LibraryFilter, LibraryFilterRule, Tag
from smplfrm.services.library_filter.exceptions import (
    DuplicateRule,
    LibraryFilterImmutable,
    LibraryFilterNotFound,
    TagNotFound,
)
from smplfrm.services.library_filter.rule_service import LibraryFilterRuleService


class LibraryFilterRuleServiceTestBase(TestCase):
    def setUp(self):
        self.service = LibraryFilterRuleService()
        self.library_filter = LibraryFilter.objects.create(name="frame")
        self.frame = Tag.objects.create(value="frame", display_value="Frame")
        self.beach = Tag.objects.create(value="beach", display_value="Beach")

    def create_tag_rule(self, library_filter=None, tag=None):
        return self.service.create(
            {
                "rule_type": LibraryFilterRule.RuleType.TAG,
                "library_filter_id": (
                    library_filter or self.library_filter
                ).external_id,
                "tag_id": (tag or self.frame).external_id,
            }
        )


class TestCreate(LibraryFilterRuleServiceTestBase):
    def test_create_tag_rule(self):
        rule = self.create_tag_rule()

        self.assertEqual(rule.library_filter, self.library_filter)
        self.assertEqual(rule.tag, self.frame)
        self.assertEqual(rule.rule_type, "tag")

    def test_unknown_or_deleted_filter_is_not_found(self):
        gone = LibraryFilter.objects.create(name="gone", deleted=True)
        for filter_id in ("does-not-exist", gone.external_id):
            with self.subTest(filter_id=filter_id):
                with self.assertRaises(LibraryFilterNotFound):
                    self.service.create(
                        {
                            "rule_type": "tag",
                            "library_filter_id": filter_id,
                            "tag_id": self.frame.external_id,
                        }
                    )

    def test_unknown_or_deleted_tag_is_not_found(self):
        gone = Tag.objects.create(value="gone", deleted=True)
        for tag_id in ("does-not-exist", gone.external_id):
            with self.subTest(tag_id=tag_id):
                with self.assertRaises(TagNotFound):
                    self.service.create(
                        {
                            "rule_type": "tag",
                            "library_filter_id": self.library_filter.external_id,
                            "tag_id": tag_id,
                        }
                    )

    def test_duplicate_tag_on_the_same_filter_is_rejected(self):
        self.create_tag_rule()

        with self.assertRaises(DuplicateRule):
            self.create_tag_rule()

    def test_database_duplicate_is_reported_as_duplicate_rule(self):
        """A concurrent insert that passes the pre-check still maps cleanly."""
        self.create_tag_rule()

        with mock.patch.object(
            LibraryFilterRuleService, "_tag_in_use", return_value=False
        ):
            with self.assertRaises(DuplicateRule):
                self.create_tag_rule()

    def test_tag_can_be_reused_after_its_rule_is_deleted(self):
        rule = self.create_tag_rule()
        self.service.delete(rule.external_id)

        self.create_tag_rule()

        self.assertEqual(LibraryFilterRule.objects.filter(deleted=False).count(), 1)


class TestReplace(LibraryFilterRuleServiceTestBase):
    def test_change_tag(self):
        rule = self.create_tag_rule()

        self.service.replace(
            rule,
            {
                "library_filter_id": self.library_filter.external_id,
                "tag_id": self.beach.external_id,
            },
        )

        self.assertEqual(LibraryFilterRule.objects.get(pk=rule.pk).tag, self.beach)

    def test_keeping_its_own_tag_is_allowed(self):
        rule = self.create_tag_rule()

        self.service.replace(
            rule,
            {
                "library_filter_id": self.library_filter.external_id,
                "tag_id": self.frame.external_id,
            },
        )

        self.assertEqual(LibraryFilterRule.objects.get(pk=rule.pk).tag, self.frame)

    def test_tag_used_by_another_rule_on_the_filter_is_rejected(self):
        rule = self.create_tag_rule()
        self.create_tag_rule(tag=self.beach)

        with self.assertRaises(DuplicateRule):
            self.service.replace(
                rule,
                {
                    "library_filter_id": self.library_filter.external_id,
                    "tag_id": self.beach.external_id,
                },
            )

    def test_unknown_tag_is_rejected(self):
        rule = self.create_tag_rule()

        with self.assertRaises(TagNotFound):
            self.service.replace(
                rule,
                {
                    "library_filter_id": self.library_filter.external_id,
                    "tag_id": "does-not-exist",
                },
            )

    def test_moving_to_another_filter_is_rejected(self):
        rule = self.create_tag_rule()
        other = LibraryFilter.objects.create(name="other")

        with self.assertRaises(LibraryFilterImmutable):
            self.service.replace(
                rule,
                {
                    "library_filter_id": other.external_id,
                    "tag_id": self.frame.external_id,
                },
            )


class TestDelete(LibraryFilterRuleServiceTestBase):
    def activate(self):
        self.library_filter.is_active = True
        self.library_filter.save()

    def filter_is_active(self):
        return LibraryFilter.objects.get(pk=self.library_filter.pk).is_active

    def test_delete_is_soft(self):
        rule = self.create_tag_rule()

        self.service.delete(rule.external_id)

        self.assertTrue(LibraryFilterRule.objects.get(pk=rule.pk).deleted)

    def test_deleting_the_last_rule_deactivates_the_active_filter(self):
        rule = self.create_tag_rule()
        self.activate()

        self.service.delete(rule.external_id)

        self.assertFalse(self.filter_is_active())

    def test_deleting_one_of_several_rules_keeps_the_filter_active(self):
        rule = self.create_tag_rule()
        self.create_tag_rule(tag=self.beach)
        self.activate()

        self.service.delete(rule.external_id)

        self.assertTrue(self.filter_is_active())

    def test_destroying_the_last_rule_deactivates_the_active_filter(self):
        rule = self.create_tag_rule()
        self.activate()

        self.service.destroy(rule.external_id)

        self.assertFalse(LibraryFilterRule.objects.exists())
        self.assertFalse(self.filter_is_active())

    def test_delete_unknown_id_is_a_no_op(self):
        self.service.delete("does-not-exist")
        self.service.destroy("does-not-exist")


class TestReadAndList(LibraryFilterRuleServiceTestBase):
    def test_read_hides_deleted(self):
        rule = self.create_tag_rule()
        self.service.delete(rule.external_id)

        with self.assertRaises(LibraryFilterRule.DoesNotExist):
            self.service.read(rule.external_id)
        self.assertEqual(self.service.read(rule.external_id, deleted=True), rule)

    def test_list_for_api_filters(self):
        other = LibraryFilter.objects.create(name="other")
        mine = self.create_tag_rule()
        theirs = self.create_tag_rule(library_filter=other)
        gone = self.create_tag_rule(tag=self.beach)
        self.service.delete(gone.external_id)

        self.assertEqual(list(self.service.list_for_api()), [mine, theirs])
        self.assertEqual(
            list(
                self.service.list_for_api(
                    library_filter_id=self.library_filter.external_id
                )
            ),
            [mine],
        )
        self.assertEqual(len(self.service.list_for_api(rule_type="tag")), 2)
        self.assertEqual(len(self.service.list_for_api(rule_type="date")), 0)

    def test_update_saves_the_row(self):
        rule = self.create_tag_rule()
        rule.tag = self.beach

        self.service.update(rule)

        self.assertEqual(LibraryFilterRule.objects.get(pk=rule.pk).tag, self.beach)

    def test_list_filters_on_kwargs(self):
        rule = self.create_tag_rule()

        self.assertEqual(list(self.service.list(tag=self.frame)), [rule])
