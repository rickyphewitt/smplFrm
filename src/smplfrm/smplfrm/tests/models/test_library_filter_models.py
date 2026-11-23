from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from smplfrm.models import LibraryFilter, LibraryFilterRule, LibraryFilterSettings, Tag


class TestLibraryFilterConstraints(TestCase):
    def test_only_one_filter_can_be_active(self):
        LibraryFilter.objects.create(name="a", is_active=True)

        with self.assertRaises(IntegrityError), transaction.atomic():
            LibraryFilter.objects.create(name="b", is_active=True)

    def test_many_filters_can_be_inactive(self):
        LibraryFilter.objects.create(name="a")
        LibraryFilter.objects.create(name="b")

        self.assertEqual(LibraryFilter.objects.count(), 2)

    def test_names_are_unique_among_live_filters(self):
        LibraryFilter.objects.create(name="frame")

        with self.assertRaises(IntegrityError), transaction.atomic():
            LibraryFilter.objects.create(name="frame")

    def test_deleted_filter_name_can_be_reused(self):
        LibraryFilter.objects.create(name="frame", deleted=True)

        LibraryFilter.objects.create(name="frame")

        self.assertEqual(LibraryFilter.objects.filter(name="frame").count(), 2)


class TestLibraryFilterRuleConstraints(TestCase):
    def setUp(self):
        self.library_filter = LibraryFilter.objects.create(name="frame")
        self.tag = Tag.objects.create(value="frame", display_value="Frame")

    def test_rule_type_defaults_to_tag(self):
        rule = LibraryFilterRule.objects.create(
            library_filter=self.library_filter, tag=self.tag
        )

        self.assertEqual(rule.rule_type, LibraryFilterRule.RuleType.TAG)

    def test_same_tag_twice_on_one_filter_is_rejected(self):
        LibraryFilterRule.objects.create(
            library_filter=self.library_filter, tag=self.tag
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            LibraryFilterRule.objects.create(
                library_filter=self.library_filter, tag=self.tag
            )

    def test_deleted_rule_does_not_block_a_new_one(self):
        LibraryFilterRule.objects.create(
            library_filter=self.library_filter, tag=self.tag, deleted=True
        )

        LibraryFilterRule.objects.create(
            library_filter=self.library_filter, tag=self.tag
        )

        self.assertEqual(LibraryFilterRule.objects.count(), 2)

    def test_same_tag_on_different_filters_is_allowed(self):
        other = LibraryFilter.objects.create(name="other")
        LibraryFilterRule.objects.create(
            library_filter=self.library_filter, tag=self.tag
        )

        LibraryFilterRule.objects.create(library_filter=other, tag=self.tag)

        self.assertEqual(LibraryFilterRule.objects.count(), 2)

    def test_tag_in_use_by_a_rule_cannot_be_hard_deleted(self):
        LibraryFilterRule.objects.create(
            library_filter=self.library_filter, tag=self.tag
        )

        with self.assertRaises(ProtectedError):
            self.tag.delete()


class TestLibraryFilterSettingsSeed(TestCase):
    def test_migration_seeds_one_disabled_row(self):
        rows = list(LibraryFilterSettings.objects.all())

        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0].enabled)
        self.assertEqual(len(rows[0].external_id), 16)
