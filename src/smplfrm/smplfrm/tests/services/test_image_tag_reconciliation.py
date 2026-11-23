"""End-to-end: tags read from real image files and stored per image."""

import os
import tempfile

from django.test import TestCase

from smplfrm.models import Image, ImageTag, Tag
from smplfrm.services.image_tag_service import ImageTagService
from smplfrm.services.library.tag_extractor import TagExtractor
from smplfrm.tests.tag_image_fixtures import write_tagged_image, xmp_packet


class TestImageTagReconciliation(TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.extractor = TagExtractor()
        self.service = ImageTagService()

    def ingest(self, file_name, **metadata):
        path = os.path.join(self._tmp.name, file_name)
        write_tagged_image(path, **metadata)
        image, _ = Image.objects.get_or_create(
            file_name=file_name,
            file_path=path,
            defaults={"name": file_name},
        )
        self.service.sync(image, self.extractor.extract(path))
        return image

    def test_same_tag_from_different_sources_is_one_tag(self):
        image_a = self.ingest("a.jpg", xmp=xmp_packet(subjects=["Family"]))
        image_b = self.ingest("b.jpg", iptc_keywords=[b"family"])

        self.assertEqual(list(Tag.objects.values_list("value", flat=True)), ["family"])
        self.assertEqual(ImageTag.objects.get(image=image_a).sources, ["xmp"])
        self.assertEqual(ImageTag.objects.get(image=image_b).sources, ["iptc"])

    def test_hierarchical_and_flat_subject_merge_into_one_link(self):
        image = self.ingest(
            "alice.jpg",
            xmp=xmp_packet(
                subjects=["Alice"],
                hierarchical=["People|Family|Alice", "Events|Birthdays|Alice"],
            ),
        )

        self.assertEqual(list(Tag.objects.values_list("value", flat=True)), ["alice"])
        link = ImageTag.objects.get(image=image)
        self.assertEqual(link.sources, ["xmp"])
        self.assertEqual(
            link.raw_hierarchy, ["People|Family|Alice", "Events|Birthdays|Alice"]
        )

    def test_rescan_without_tag_removes_link_and_keeps_tag(self):
        image = self.ingest("frame.jpg", xp_keywords=["frame"])
        self.assertTrue(ImageTag.objects.filter(image=image).exists())

        self.ingest("frame.jpg")

        self.assertFalse(ImageTag.objects.filter(image=image).exists())
        self.assertTrue(Tag.objects.filter(value="frame").exists())
