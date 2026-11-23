import os
import tempfile
from unittest import mock

from django.test import SimpleTestCase

from smplfrm.services.library.tag_extractor import MAX_XMP_BYTES, TagExtractor
from smplfrm.tests.tag_image_fixtures import write_tagged_image, xmp_packet


class TagExtractorTestBase(SimpleTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.extractor = TagExtractor()

    def path(self, name: str) -> str:
        return os.path.join(self._tmp.name, name)

    def by_canonical(self, extracted):
        return {tag.canonical: tag for tag in extracted}


class TestTagExtractorSources(TagExtractorTestBase):
    def test_reads_every_source_and_merges_provenance(self):
        path = write_tagged_image(
            self.path("all.jpg"),
            xp_keywords=["Family", "Beach"],
            iptc_keywords=[b"family", b"Frame"],
            xmp=xmp_packet(
                subjects=["FAMILY", "Sunset"],
                hierarchical=["People|Family|Alice"],
            ),
        )

        tags = self.by_canonical(self.extractor.extract(path))

        self.assertEqual(set(tags), {"family", "beach", "frame", "sunset", "alice"})
        self.assertEqual(tags["family"].sources, ("exif", "iptc", "xmp"))
        self.assertEqual(tags["beach"].sources, ("exif",))
        self.assertEqual(tags["frame"].sources, ("iptc",))
        self.assertEqual(tags["sunset"].sources, ("xmp",))
        self.assertEqual(tags["alice"].sources, ("xmp",))

    def test_display_value_is_first_seen_form(self):
        path = write_tagged_image(
            self.path("display.jpg"),
            xp_keywords=["Family"],
            iptc_keywords=[b"FAMILY"],
        )

        tags = self.by_canonical(self.extractor.extract(path))

        self.assertEqual(tags["family"].display, "Family")

    def test_hierarchical_subject_keeps_every_path_for_the_leaf(self):
        path = write_tagged_image(
            self.path("hier.jpg"),
            xmp=xmp_packet(
                subjects=["Alice"],
                hierarchical=["People|Family|Alice", "Events|Birthdays|Alice"],
            ),
        )

        extracted = self.extractor.extract(path)

        self.assertEqual(len(extracted), 1)
        alice = extracted[0]
        self.assertEqual(alice.canonical, "alice")
        self.assertEqual(alice.sources, ("xmp",))
        self.assertEqual(
            alice.raw_hierarchy,
            ("People|Family|Alice", "Events|Birthdays|Alice"),
        )

    def test_flat_tags_have_no_hierarchy(self):
        path = write_tagged_image(self.path("flat.jpg"), xp_keywords=["Beach"])

        (beach,) = self.extractor.extract(path)

        self.assertEqual(beach.raw_hierarchy, ())

    def test_dc_subject_in_a_seq_container_is_read(self):
        path = write_tagged_image(
            self.path("seq.jpg"),
            xmp=xmp_packet(subjects=["Lake"], subject_container="Seq"),
        )

        self.assertEqual([t.canonical for t in self.extractor.extract(path)], ["lake"])

    def test_iptc_falls_back_to_latin_1(self):
        path = write_tagged_image(self.path("latin1.jpg"), iptc_keywords=[b"caf\xe9"])

        self.assertEqual([t.canonical for t in self.extractor.extract(path)], ["café"])

    def test_iptc_utf8_is_decoded(self):
        path = write_tagged_image(
            self.path("utf8.jpg"), iptc_keywords=["café".encode("utf-8")]
        )

        self.assertEqual([t.canonical for t in self.extractor.extract(path)], ["café"])

    def test_png_exif_and_xmp_are_read(self):
        path = write_tagged_image(
            self.path("tagged.png"),
            image_format="PNG",
            xp_keywords=["Garden"],
            xmp=xmp_packet(subjects=["Flowers"]),
        )

        tags = self.by_canonical(self.extractor.extract(path))

        self.assertEqual(set(tags), {"garden", "flowers"})

    def test_unusable_values_are_dropped_and_the_rest_kept(self):
        path = write_tagged_image(
            self.path("junk.jpg"),
            xp_keywords=["   ", "a" * 201, "Keep"],
        )

        self.assertEqual([t.canonical for t in self.extractor.extract(path)], ["keep"])

    def test_image_without_metadata_has_no_tags(self):
        path = write_tagged_image(self.path("plain.jpg"))

        self.assertEqual(self.extractor.extract(path), [])


class TestTagExtractorFailureIsolation(TagExtractorTestBase):
    """A broken metadata source must not hide tags from the other sources."""

    def _all_sources_image(self):
        return write_tagged_image(
            self.path("isolation.jpg"),
            xp_keywords=["FromExif"],
            iptc_keywords=[b"FromIptc"],
            xmp=xmp_packet(subjects=["FromXmp"]),
        )

    def test_exif_failure_keeps_iptc_and_xmp(self):
        path = self._all_sources_image()
        with mock.patch("PIL.Image.Image.getexif", side_effect=SyntaxError("bad exif")):
            tags = self.by_canonical(self.extractor.extract(path))

        self.assertEqual(set(tags), {"fromiptc", "fromxmp"})

    def test_iptc_failure_keeps_exif_and_xmp(self):
        path = self._all_sources_image()
        with mock.patch(
            "smplfrm.services.library.tag_extractor.IptcImagePlugin.getiptcinfo",
            side_effect=ValueError("bad iptc"),
        ):
            tags = self.by_canonical(self.extractor.extract(path))

        self.assertEqual(set(tags), {"fromexif", "fromxmp"})

    def test_malformed_xmp_keeps_exif_and_iptc(self):
        path = write_tagged_image(
            self.path("badxmp.jpg"),
            xp_keywords=["FromExif"],
            iptc_keywords=[b"FromIptc"],
            xmp="<x:xmpmeta><unclosed>",
        )

        tags = self.by_canonical(self.extractor.extract(path))

        self.assertEqual(set(tags), {"fromexif", "fromiptc"})

    def test_xmp_with_doctype_is_skipped(self):
        packet = '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "boom">]>' + xmp_packet(
            subjects=["FromXmp"]
        )
        path = write_tagged_image(
            self.path("doctype.jpg"), xp_keywords=["FromExif"], xmp=packet
        )

        tags = self.by_canonical(self.extractor.extract(path))

        self.assertEqual(set(tags), {"fromexif"})

    def test_oversized_xmp_is_skipped(self):
        padding = "<!-- " + "x" * MAX_XMP_BYTES + " -->"
        path = write_tagged_image(
            self.path("huge.png"),
            image_format="PNG",
            xp_keywords=["FromExif"],
            xmp=xmp_packet(subjects=["FromXmp"]) + padding,
        )

        tags = self.by_canonical(self.extractor.extract(path))

        self.assertEqual(set(tags), {"fromexif"})

    def test_unreadable_file_returns_no_tags(self):
        path = self.path("not_an_image.jpg")
        with open(path, "wb") as fh:
            fh.write(b"definitely not a jpeg")

        self.assertEqual(self.extractor.extract(path), [])

    def test_missing_file_returns_no_tags(self):
        self.assertEqual(self.extractor.extract(self.path("missing.jpg")), [])
