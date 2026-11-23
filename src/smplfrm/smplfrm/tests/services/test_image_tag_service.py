from django.test import TestCase

from smplfrm.models import Image, ImageTag, Tag
from smplfrm.models.tag import TAG_VALUE_MAX_LENGTH
from smplfrm.services.image_tag_service import ImageTagService
from smplfrm.services.library.canonicalize import MAX_TAG_LENGTH
from smplfrm.services.library.tag_extractor import ExtractedTag


def extracted(canonical, display=None, sources=("xmp",), raw_hierarchy=()):
    return ExtractedTag(
        canonical=canonical,
        display=display if display is not None else canonical.title(),
        sources=tuple(sources),
        raw_hierarchy=tuple(raw_hierarchy),
    )


class ImageTagServiceTestBase(TestCase):
    def setUp(self):
        self.service = ImageTagService()
        self.image = Image.objects.create(
            name="a.jpg", file_name="a.jpg", file_path="/library/a.jpg"
        )

    def tag_values(self, image):
        return set(
            ImageTag.objects.filter(image=image).values_list("tag__value", flat=True)
        )


class TestImageTagServiceSync(ImageTagServiceTestBase):
    def test_creates_tags_and_links(self):
        self.service.sync(
            self.image,
            [extracted("family", "Family", ("exif", "xmp")), extracted("beach")],
        )

        self.assertEqual(self.tag_values(self.image), {"family", "beach"})
        family = Tag.objects.get(value="family")
        self.assertEqual(family.display_value, "Family")
        link = ImageTag.objects.get(image=self.image, tag=family)
        self.assertEqual(link.sources, ["exif", "xmp"])
        self.assertEqual(link.raw_hierarchy, [])

    def test_reuses_existing_tag_across_images(self):
        other = Image.objects.create(
            name="b.jpg", file_name="b.jpg", file_path="/library/b.jpg"
        )

        self.service.sync(self.image, [extracted("family", "Family")])
        self.service.sync(other, [extracted("family", "FAMILY")])

        self.assertEqual(Tag.objects.filter(value="family").count(), 1)
        self.assertEqual(Tag.objects.get(value="family").display_value, "Family")
        self.assertEqual(ImageTag.objects.filter(tag__value="family").count(), 2)

    def test_stores_hierarchy_paths(self):
        paths = ("People|Family|Alice", "Events|Birthdays|Alice")
        self.service.sync(self.image, [extracted("alice", raw_hierarchy=paths)])

        link = ImageTag.objects.get(image=self.image)
        self.assertEqual(link.raw_hierarchy, list(paths))

    def test_updates_sources_and_hierarchy_when_they_change(self):
        self.service.sync(self.image, [extracted("alice", sources=("exif",))])
        self.service.sync(
            self.image,
            [extracted("alice", sources=("iptc", "xmp"), raw_hierarchy=("P|Alice",))],
        )

        link = ImageTag.objects.get(image=self.image)
        self.assertEqual(link.sources, ["iptc", "xmp"])
        self.assertEqual(link.raw_hierarchy, ["P|Alice"])

    def test_removes_links_no_longer_present_but_keeps_tags(self):
        self.service.sync(self.image, [extracted("frame"), extracted("beach")])
        self.service.sync(self.image, [extracted("beach")])

        self.assertEqual(self.tag_values(self.image), {"beach"})
        self.assertTrue(Tag.objects.filter(value="frame").exists())

    def test_empty_extraction_removes_all_links(self):
        self.service.sync(self.image, [extracted("frame")])
        self.service.sync(self.image, [])

        self.assertEqual(self.tag_values(self.image), set())
        self.assertTrue(Tag.objects.filter(value="frame").exists())

    def test_only_touches_links_for_the_given_image(self):
        other = Image.objects.create(
            name="b.jpg", file_name="b.jpg", file_path="/library/b.jpg"
        )
        self.service.sync(other, [extracted("frame")])

        self.service.sync(self.image, [])

        self.assertEqual(self.tag_values(other), {"frame"})

    def test_unchanged_sync_does_not_rewrite_links(self):
        self.service.sync(self.image, [extracted("frame")])
        before = ImageTag.objects.get(image=self.image).updated

        self.service.sync(self.image, [extracted("frame")])

        self.assertEqual(ImageTag.objects.get(image=self.image).updated, before)

    def test_revives_soft_deleted_tag(self):
        Tag.objects.create(value="frame", display_value="Frame", deleted=True)

        self.service.sync(self.image, [extracted("frame")])

        self.assertFalse(Tag.objects.get(value="frame").deleted)

    def test_revives_soft_deleted_link(self):
        self.service.sync(self.image, [extracted("frame")])
        ImageTag.objects.filter(image=self.image).update(deleted=True)

        self.service.sync(self.image, [extracted("frame")])

        self.assertFalse(ImageTag.objects.get(image=self.image).deleted)

    def test_backfills_empty_display_value(self):
        Tag.objects.create(value="frame", display_value="")

        self.service.sync(self.image, [extracted("frame", "Frame")])

        self.assertEqual(Tag.objects.get(value="frame").display_value, "Frame")


class TestImageTagServiceCrud(ImageTagServiceTestBase):
    def setUp(self):
        super().setUp()
        self.tag = Tag.objects.create(value="frame", display_value="Frame")

    def test_create_and_read(self):
        link = self.service.create(
            {"image": self.image, "tag": self.tag, "sources": ["exif"]}
        )

        self.assertEqual(self.service.read(link.external_id), link)

    def test_list_filters(self):
        link = self.service.create({"image": self.image, "tag": self.tag})

        self.assertEqual(list(self.service.list(image=self.image)), [link])
        self.assertEqual(self.service.list().count(), 1)

    def test_update(self):
        link = self.service.create({"image": self.image, "tag": self.tag})
        link.sources = ["iptc"]

        self.service.update(link)

        self.assertEqual(ImageTag.objects.get(pk=link.pk).sources, ["iptc"])

    def test_delete_is_soft(self):
        link = self.service.create({"image": self.image, "tag": self.tag})

        self.service.delete(link.external_id)

        self.assertTrue(self.service.read(link.external_id, deleted=True).deleted)

    def test_destroy_removes_row(self):
        link = self.service.create({"image": self.image, "tag": self.tag})

        self.service.destroy(link.external_id)

        self.assertFalse(ImageTag.objects.filter(pk=link.pk).exists())

    def test_delete_and_destroy_ignore_unknown_ids(self):
        self.service.delete("does-not-exist")
        self.service.destroy("does-not-exist")


class TestTagLengthLimitsMatch(TestCase):
    def test_model_and_canonicalizer_agree_on_max_length(self):
        self.assertEqual(TAG_VALUE_MAX_LENGTH, MAX_TAG_LENGTH)
