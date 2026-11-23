from django.test import TestCase

from smplfrm.models import LibraryFilter, LibraryFilterRule, Tag
from smplfrm.services.library_filter.exceptions import RuleRequired, UniqueName
from smplfrm.services.library_filter.service import LibraryFilterService


class LibraryFilterServiceTestBase(TestCase):
    def setUp(self):
        self.service = LibraryFilterService()
        self.tag = Tag.objects.create(value="frame", display_value="Frame")

    def make_filter(self, name, is_active=False, rules=0, deleted=False):
        library_filter = LibraryFilter.objects.create(
            name=name, is_active=is_active, deleted=deleted
        )
        for i in range(rules):
            tag = Tag.objects.create(value=f"{name}-{i}")
            LibraryFilterRule.objects.create(library_filter=library_filter, tag=tag)
        return library_filter

    def refresh(self, library_filter):
        return LibraryFilter.objects.get(pk=library_filter.pk)


class TestCreate(LibraryFilterServiceTestBase):
    def test_create_defaults(self):
        library_filter = self.service.create({"name": "frame"})

        self.assertEqual(library_filter.description, "")
        self.assertFalse(library_filter.is_active)

    def test_create_active_is_rejected_because_it_has_no_rules(self):
        with self.assertRaises(RuleRequired):
            self.service.create({"name": "frame", "is_active": True})

        self.assertFalse(LibraryFilter.objects.exists())

    def test_create_duplicate_name_is_rejected(self):
        self.make_filter("frame")

        with self.assertRaises(UniqueName):
            self.service.create({"name": "frame"})

    def test_create_reuses_a_deleted_name(self):
        self.make_filter("frame", deleted=True)

        self.service.create({"name": "frame"})

        self.assertEqual(LibraryFilter.objects.filter(deleted=False).count(), 1)


class TestReplace(LibraryFilterServiceTestBase):
    def test_replace_resets_omitted_fields(self):
        library_filter = self.make_filter("frame", is_active=True, rules=1)
        library_filter.description = "x"
        library_filter.save()

        self.service.replace(library_filter, {"name": "frame"})

        stored = self.refresh(library_filter)
        self.assertEqual(stored.description, "")
        self.assertFalse(stored.is_active)

    def test_activation_deactivates_the_previous_active_filter(self):
        previous = self.make_filter("previous", is_active=True, rules=1)
        library_filter = self.make_filter("frame", rules=1)

        self.service.replace(library_filter, {"name": "frame", "is_active": True})

        self.assertTrue(self.refresh(library_filter).is_active)
        self.assertFalse(self.refresh(previous).is_active)

    def test_activation_without_live_rules_is_rejected(self):
        previous = self.make_filter("previous", is_active=True, rules=1)
        library_filter = self.make_filter("frame", rules=1)
        LibraryFilterRule.objects.filter(library_filter=library_filter).update(
            deleted=True
        )

        with self.assertRaises(RuleRequired):
            self.service.replace(library_filter, {"name": "frame", "is_active": True})

        self.assertFalse(self.refresh(library_filter).is_active)
        self.assertTrue(self.refresh(previous).is_active)

    def test_replace_keeps_an_already_active_filter_active(self):
        library_filter = self.make_filter("frame", is_active=True, rules=1)

        self.service.replace(library_filter, {"name": "renamed", "is_active": True})

        stored = self.refresh(library_filter)
        self.assertTrue(stored.is_active)
        self.assertEqual(stored.name, "renamed")

    def test_rename_to_a_taken_name_is_rejected(self):
        self.make_filter("taken")
        library_filter = self.make_filter("frame")

        with self.assertRaises(UniqueName):
            self.service.replace(library_filter, {"name": "taken"})

    def test_keeping_its_own_name_is_allowed(self):
        library_filter = self.make_filter("frame")

        self.service.replace(library_filter, {"name": "frame", "description": "d"})

        self.assertEqual(self.refresh(library_filter).description, "d")


class TestActivate(LibraryFilterServiceTestBase):
    def test_activate_by_external_id(self):
        library_filter = self.make_filter("frame", rules=1)

        self.service.activate(library_filter.external_id)

        self.assertTrue(self.refresh(library_filter).is_active)

    def test_activate_without_rules_is_rejected(self):
        library_filter = self.make_filter("frame")

        with self.assertRaises(RuleRequired):
            self.service.activate(library_filter.external_id)


class TestDelete(LibraryFilterServiceTestBase):
    def test_delete_active_filter_deactivates_and_cascades_to_rules(self):
        library_filter = self.make_filter("frame", is_active=True, rules=2)

        self.service.delete(library_filter.external_id)

        stored = self.refresh(library_filter)
        self.assertTrue(stored.deleted)
        self.assertFalse(stored.is_active)
        self.assertFalse(
            LibraryFilterRule.objects.filter(
                library_filter=library_filter, deleted=False
            ).exists()
        )

    def test_delete_unknown_id_is_a_no_op(self):
        self.service.delete("does-not-exist")

    def test_destroy_removes_filter_and_rules(self):
        library_filter = self.make_filter("frame", rules=1)

        self.service.destroy(library_filter.external_id)

        self.assertFalse(LibraryFilter.objects.exists())
        self.assertFalse(LibraryFilterRule.objects.exists())


class TestReadAndList(LibraryFilterServiceTestBase):
    def test_read_hides_deleted(self):
        library_filter = self.make_filter("frame", deleted=True)

        with self.assertRaises(LibraryFilter.DoesNotExist):
            self.service.read(library_filter.external_id)
        self.assertEqual(
            self.service.read(library_filter.external_id, deleted=True),
            library_filter,
        )

    def test_list_for_api_hides_deleted_and_orders_by_name(self):
        self.make_filter("b")
        self.make_filter("a")
        self.make_filter("gone", deleted=True)

        names = [f.name for f in self.service.list_for_api()]

        self.assertEqual(names, ["a", "b"])

    def test_list_for_api_filters_on_is_active(self):
        active = self.make_filter("active", is_active=True, rules=1)
        self.make_filter("idle")

        self.assertEqual(list(self.service.list_for_api(is_active=True)), [active])
        self.assertEqual(
            [f.name for f in self.service.list_for_api(is_active=False)], ["idle"]
        )

    def test_list_filters_on_kwargs(self):
        library_filter = self.make_filter("frame")

        self.assertEqual(list(self.service.list(name="frame")), [library_filter])
