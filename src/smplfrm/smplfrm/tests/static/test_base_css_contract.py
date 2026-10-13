"""Contract test for base.css.

base.css is structural, theme-neutral CSS: no color literal, no font-family
declaration other than the icon font, no border-radius, and no box-shadow.
Colors, type, radii, and shadows belong to themes.
"""

import re
from pathlib import Path

from django.test import SimpleTestCase

BASE_CSS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "static" / "css" / "base.css"
)

COLOR_PATTERN = re.compile(
    r"(?:^|[\s:])(#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\))"
)


class TestBaseCssContract(SimpleTestCase):
    def setUp(self):
        self.css_text = BASE_CSS_PATH.read_text()
        # Strip comments so a mention inside a /* ... */ block cannot
        # produce a false positive or false negative.
        self.css_text_no_comments = re.sub(r"/\*.*?\*/", "", self.css_text, flags=re.S)

    def test_no_color_literals(self):
        matches = COLOR_PATTERN.findall(self.css_text_no_comments)
        self.assertEqual(matches, [], f"Unexpected color literals: {matches}")

    def test_no_font_family_declarations(self):
        self.assertNotIn("font-family", self.css_text_no_comments)

    def test_no_border_radius(self):
        self.assertNotIn("border-radius", self.css_text_no_comments)
        self.assertNotIn("radius", self.css_text_no_comments)

    def test_no_box_shadow(self):
        self.assertNotIn("box-shadow", self.css_text_no_comments)
        self.assertNotIn("shadow", self.css_text_no_comments)
