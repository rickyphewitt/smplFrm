from django.test import TestCase

from smplfrm.services import ImageMetadataService
from smplfrm.tests.library_filter_fixtures import (
    activate_filter,
    make_image,
    set_filtering,
)


class TestImageMetadataVisibleQueryset(TestCase):
    def setUp(self):
        self.service = ImageMetadataService()
        self.framed = make_image("framed.jpg", tags=["frame"], with_meta=True)
        self.plain = make_image("plain.jpg", with_meta=True)
        self.deleted = make_image(
            "gone.jpg", tags=["frame"], with_meta=True, deleted=True
        )

    def images(self):
        return {meta.image for meta in self.service.visible_queryset()}

    def test_filtering_off_returns_metadata_for_live_images(self):
        self.assertEqual(self.images(), {self.framed, self.plain})

    def test_filtering_on_returns_metadata_for_matching_images(self):
        set_filtering(True)
        activate_filter("frame")

        self.assertEqual(self.images(), {self.framed})

    def test_filtering_on_without_active_filter_returns_nothing(self):
        set_filtering(True)

        self.assertEqual(self.images(), set())

    def test_soft_deleted_metadata_is_hidden(self):
        meta = self.framed.meta
        meta.deleted = True
        meta.save()

        self.assertEqual(self.images(), {self.plain})
