from django.test import TestCase

from smplfrm.models import Image, ImageTag, Tag
from smplfrm.services.tag_service import TagService


class TestTagService(TestCase):
    def setUp(self):
        self.service = TagService()
        self.frame = Tag.objects.create(value="frame", display_value="Frame")
        self.beach = Tag.objects.create(value="beach", display_value="Beach")

    def make_image(self, name, deleted=False):
        return Image.objects.create(
            name=name, file_name=name, file_path=f"/library/{name}", deleted=deleted
        )

    def test_read(self):
        self.assertEqual(self.service.read(self.frame.external_id), self.frame)

    def test_read_hides_deleted_unless_asked(self):
        self.frame.deleted = True
        self.frame.save()

        with self.assertRaises(Tag.DoesNotExist):
            self.service.read(self.frame.external_id)
        self.assertEqual(
            self.service.read(self.frame.external_id, deleted=True), self.frame
        )

    def test_list(self):
        self.assertEqual(self.service.list().count(), 2)
        self.assertEqual(list(self.service.list(value="beach")), [self.beach])

    def test_list_with_usage_counts_links_on_non_deleted_images(self):
        first = self.make_image("1.jpg")
        second = self.make_image("2.jpg")
        ImageTag.objects.create(image=first, tag=self.frame)
        ImageTag.objects.create(image=second, tag=self.frame)

        counts = {t.value: t.usage_count for t in self.service.list_with_usage()}
        self.assertEqual(counts, {"frame": 2, "beach": 0})

        second.deleted = True
        second.save()

        counts = {t.value: t.usage_count for t in self.service.list_with_usage()}
        self.assertEqual(counts["frame"], 1)

    def test_list_with_usage_is_ordered_by_value(self):
        values = [t.value for t in self.service.list_with_usage()]
        self.assertEqual(values, ["beach", "frame"])

    def test_list_with_usage_hides_deleted_tags(self):
        self.beach.deleted = True
        self.beach.save()

        values = [t.value for t in self.service.list_with_usage()]
        self.assertEqual(values, ["frame"])

    def test_list_with_usage_filters_on_canonical_value(self):
        self.assertEqual(
            [t.value for t in self.service.list_with_usage(value="  FRAME ")],
            ["frame"],
        )
        self.assertEqual(list(self.service.list_with_usage(value="nope")), [])
        self.assertEqual(list(self.service.list_with_usage(value="   ")), [])

    def test_mutations_are_not_supported(self):
        with self.assertRaises(NotImplementedError):
            self.service.create({"value": "x"})
        with self.assertRaises(NotImplementedError):
            self.service.update(self.frame)
        with self.assertRaises(NotImplementedError):
            self.service.delete(self.frame.external_id)
        with self.assertRaises(NotImplementedError):
            self.service.destroy(self.frame.external_id)
