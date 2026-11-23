from django.test import SimpleTestCase

from smplfrm.services.library.canonicalize import (
    MAX_TAG_LENGTH,
    canonicalize,
    normalize_display,
)


class TestCanonicalize(SimpleTestCase):
    """Tag values from different sources must collapse to one stored form."""

    def test_case_and_surrounding_whitespace_are_folded(self):
        self.assertEqual(canonicalize("  Family  "), "family")
        self.assertEqual(canonicalize("FAMILY"), "family")

    def test_casefold_handles_non_ascii_case(self):
        self.assertEqual(canonicalize("STRASSE"), canonicalize("straße"))

    def test_decomposed_and_precomposed_accents_are_equal(self):
        decomposed = "fa\u0300mily"
        precomposed = "f\u00e0mily"
        self.assertEqual(canonicalize(decomposed), canonicalize(precomposed))
        self.assertEqual(canonicalize(decomposed), "f\u00e0mily")

    def test_accents_are_kept(self):
        self.assertNotEqual(canonicalize("café"), canonicalize("cafe"))

    def test_nul_and_control_characters_are_removed(self):
        self.assertEqual(canonicalize("family\x00"), "family")
        self.assertEqual(canonicalize("fam\x07ily\x7f"), "family")

    def test_internal_whitespace_runs_collapse_to_one_space(self):
        self.assertEqual(canonicalize("new    york"), "new york")
        self.assertEqual(canonicalize("new\u00a0\u2003york"), "new york")

    def test_empty_results_are_rejected(self):
        self.assertIsNone(canonicalize(""))
        self.assertIsNone(canonicalize("   "))
        self.assertIsNone(canonicalize("\x00\x01"))

    def test_length_limit(self):
        self.assertEqual(canonicalize("a" * MAX_TAG_LENGTH), "a" * MAX_TAG_LENGTH)
        self.assertIsNone(canonicalize("a" * (MAX_TAG_LENGTH + 1)))

    def test_non_string_input_is_rejected(self):
        self.assertIsNone(canonicalize(None))
        self.assertIsNone(canonicalize(b"family"))


class TestNormalizeDisplay(SimpleTestCase):
    """The display form keeps the author's casing but is otherwise cleaned."""

    def test_keeps_case_and_cleans_whitespace_and_controls(self):
        self.assertEqual(normalize_display("  New \x00 York  "), "New York")

    def test_applies_nfc(self):
        self.assertEqual(normalize_display("Fa\u0300mily"), "F\u00e0mily")
