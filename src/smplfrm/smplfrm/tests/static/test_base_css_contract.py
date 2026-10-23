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


def _declaration(css_text, selector, prop):
    """Return the value of prop in the first rule whose selector is exactly selector."""
    pattern = re.compile(
        rf"(?:^|\}})\s*{re.escape(selector)}\s*\{{([^}}]*)\}}", flags=re.M
    )
    for match in pattern.finditer(css_text):
        decl = re.search(rf"(?:^|;|\s){re.escape(prop)}\s*:\s*([^;]+);", match.group(1))
        if decl:
            return decl.group(1).strip()
    return None


class TestToastPlacement(SimpleTestCase):
    """The three corner toasts are stacked by base.css so all can show at once.

    Placement is structural, so it lives here rather than in a theme or in
    JavaScript: every theme inherits the same non-overlapping stack.
    """

    def setUp(self):
        css = re.sub(r"/\*.*?\*/", "", BASE_CSS_PATH.read_text(), flags=re.S)
        # One line, single spaces, so multi-line selector lists match exactly.
        self.css = re.sub(r"\s+", " ", css)

    def _bottom_px(self, selector):
        value = _declaration(self.css, selector, "bottom")
        self.assertIsNotNone(value, f"{selector} has no bottom offset in base.css")
        self.assertTrue(value.endswith("px"), value)
        return int(value[:-2])

    def test_toasts_are_fixed_position(self):
        for selector in (".task-toast", ".rate-limit-toast, .app-toast"):
            with self.subTest(selector=selector):
                self.assertEqual(_declaration(self.css, selector, "position"), "fixed")

    def test_toasts_stack_task_then_rate_limit_then_action(self):
        task = self._bottom_px(".task-toast")
        rate_limit = self._bottom_px(".rate-limit-toast")
        action = self._bottom_px(".app-toast")
        self.assertLess(task, rate_limit)
        self.assertLess(rate_limit, action)


class TestIdleCursor(SimpleTestCase):
    """main.js sets body.cursor-idle after 30 seconds of pointer inactivity.

    Hiding the cursor is behaviour, not style, so base.css owns the rule and
    every theme inherits it. It must cover descendants and win over the
    `cursor: pointer` that buttons and links declare.
    """

    def test_idle_class_hides_the_cursor_everywhere(self):
        css = re.sub(r"/\*.*?\*/", "", BASE_CSS_PATH.read_text(), flags=re.S)
        css = re.sub(r"\s+", " ", css)
        value = _declaration(css, "body.cursor-idle, body.cursor-idle *", "cursor")
        self.assertEqual(value, "none !important")
