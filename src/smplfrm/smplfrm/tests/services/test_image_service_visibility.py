from unittest import mock

from django.test import TestCase

from smplfrm.models import Image, LibraryFilterRule
from smplfrm.services import ImageService
from smplfrm.tests.library_filter_fixtures import (
    activate_filter,
    make_image,
    set_filtering,
)


class ImageVisibilityTestBase(TestCase):
    def setUp(self):
        self.service = ImageService()
        self.framed = make_image("framed.jpg", tags=["frame"])
        self.beach = make_image("beach.jpg", tags=["beach"])
        self.plain = make_image("plain.jpg")
        self.deleted_framed = make_image("gone.jpg", tags=["frame"], deleted=True)

    def visible(self, **kwargs):
        return set(self.service.visible_queryset(**kwargs))


class TestVisibleQueryset(ImageVisibilityTestBase):
    def test_filtering_off_shows_every_live_image(self):
        self.assertEqual(self.visible(), {self.framed, self.beach, self.plain})

    def test_filtering_off_ignores_an_active_filter(self):
        activate_filter("frame")

        self.assertEqual(self.visible(), {self.framed, self.beach, self.plain})

    def test_filtering_off_can_include_deleted(self):
        self.assertEqual(
            self.visible(include_deleted=True),
            {self.framed, self.beach, self.plain, self.deleted_framed},
        )

    def test_filtering_on_without_active_filter_shows_nothing(self):
        set_filtering(True)

        self.assertEqual(self.visible(), set())

    def test_filtering_on_with_inactive_filter_shows_nothing(self):
        set_filtering(True)
        library_filter = activate_filter("frame")
        library_filter.is_active = False
        library_filter.save()

        self.assertEqual(self.visible(), set())

    def test_filtering_on_shows_images_matching_the_active_filter(self):
        set_filtering(True)
        activate_filter("frame")

        self.assertEqual(self.visible(), {self.framed})

    def test_rules_are_combined_with_any(self):
        set_filtering(True)
        activate_filter("frame", "beach")

        self.assertEqual(self.visible(), {self.framed, self.beach})

    def test_image_matching_several_rules_appears_once(self):
        both = make_image("both.jpg", tags=["frame", "beach"])
        set_filtering(True)
        activate_filter("frame", "beach")

        ids = list(self.service.visible_queryset().values_list("pk", flat=True))

        self.assertEqual(ids.count(both.pk), 1)
        self.assertEqual(self.service.visible_queryset().count(), 3)

    def test_deleted_rules_are_ignored(self):
        set_filtering(True)
        library_filter = activate_filter("frame", "beach")
        LibraryFilterRule.objects.filter(
            library_filter=library_filter, tag__value="beach"
        ).update(deleted=True)

        self.assertEqual(self.visible(), {self.framed})

    def test_active_filter_with_no_live_rules_shows_nothing(self):
        set_filtering(True)
        library_filter = activate_filter("frame")
        LibraryFilterRule.objects.filter(library_filter=library_filter).update(
            deleted=True
        )

        self.assertEqual(self.visible(), set())

    def test_deleted_active_filter_shows_nothing(self):
        set_filtering(True)
        library_filter = activate_filter("frame")
        library_filter.deleted = True
        library_filter.save()

        self.assertEqual(self.visible(), set())

    def test_filtering_on_can_include_deleted_matches(self):
        set_filtering(True)
        activate_filter("frame")

        self.assertEqual(
            self.visible(include_deleted=True), {self.framed, self.deleted_framed}
        )

    def test_rule_type_without_a_handler_hides_everything(self):
        """An unknown rule type fails closed rather than showing every image."""
        set_filtering(True)
        library_filter = activate_filter("frame")
        LibraryFilterRule.objects.filter(library_filter=library_filter).update(
            rule_type="unknown"
        )

        self.assertEqual(self.visible(), set())

    def test_query_count(self):
        set_filtering(True)
        activate_filter("frame", "beach")

        # One query for the settings row, one for the active filter's rules,
        # one for the images themselves.
        with self.assertNumQueries(3):
            list(self.service.visible_queryset())

    def test_query_count_when_filtering_is_off(self):
        with self.assertNumQueries(2):
            list(self.service.visible_queryset())


class TestReadMethodsAreGated(ImageVisibilityTestBase):
    def setUp(self):
        super().setUp()
        set_filtering(True)
        activate_filter("frame")

    def test_read_returns_a_visible_image(self):
        self.assertEqual(self.service.read(self.framed.external_id), self.framed)

    def test_read_hides_a_filtered_out_image(self):
        with self.assertRaises(Image.DoesNotExist):
            self.service.read(self.beach.external_id)

    def test_read_can_bypass_visibility(self):
        self.assertEqual(
            self.service.read(self.beach.external_id, enforce_visibility=False),
            self.beach,
        )

    def test_read_deleted_still_requires_visibility(self):
        hidden_deleted = make_image("hidden-gone.jpg", deleted=True)

        self.assertEqual(
            self.service.read(self.deleted_framed.external_id, deleted=True),
            self.deleted_framed,
        )
        with self.assertRaises(Image.DoesNotExist):
            self.service.read(hidden_deleted.external_id, deleted=True)
        self.assertEqual(
            self.service.read(
                hidden_deleted.external_id, deleted=True, enforce_visibility=False
            ),
            hidden_deleted,
        )

    def test_get_next(self):
        self.assertEqual(list(self.service.get_next()), [self.framed])

    def test_get_ordered_images(self):
        self.assertEqual(list(self.service.get_ordered_images(None)), [self.framed])
        self.assertEqual(
            list(self.service.get_ordered_images("display_priority")), [self.framed]
        )

    def test_public_reads_use_visible_queryset(self):
        with mock.patch.object(
            ImageService,
            "visible_queryset",
            return_value=Image.objects.none(),
        ) as visible_queryset:
            self.assertEqual(list(self.service.get_next()), [])
            self.assertEqual(list(self.service.get_ordered_images(None)), [])
            with self.assertRaises(Image.DoesNotExist):
                self.service.read(self.framed.external_id)

        self.assertEqual(visible_queryset.call_count, 3)


class TestScanPathsAreNotGated(ImageVisibilityTestBase):
    def setUp(self):
        super().setUp()
        set_filtering(True)

    def test_read_by_file_name_and_file_path_ignores_filtering(self):
        self.assertEqual(
            self.service.read_by_file_name_and_file_path(
                self.beach.file_name, self.beach.file_path
            ),
            self.beach,
        )

    def test_list_ignores_filtering(self):
        self.assertEqual(self.service.list(deleted=False).count(), 3)
