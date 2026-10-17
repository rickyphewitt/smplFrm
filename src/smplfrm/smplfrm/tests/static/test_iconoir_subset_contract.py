"""Contract test for the vendored Iconoir icon subset.

static/icons/iconoir.css is a generated subset of the npm "iconoir" package,
containing only the glyphs smplFrm actually uses. Two kinds of drift are
possible and both are guarded here:

1. A glyph class referenced in the app JavaScript under static/ or in a
   template but missing from the vendored subset. The browser then renders a
   plain colored square instead of the icon (the base
   `*[class^='iconoir-']::before` rule sets size and background, but with no
   `mask-image` for that class there is nothing to mask it into a shape).
2. A vendored rule that no longer matches the pinned upstream package,
   because it was edited by hand or copied from a different version. That
   check runs only when node_modules is present (CI installs it before the
   Python suite) and is skipped otherwise, so the suite stays runnable
   without a JavaScript toolchain.
"""

import re
from pathlib import Path

from django.test import SimpleTestCase

APP_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = APP_DIR.parent.parent.parent
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"
ICONOIR_CSS_PATH = STATIC_DIR / "icons" / "iconoir.css"
UPSTREAM_CSS_PATH = REPO_ROOT / "node_modules" / "iconoir" / "css" / "iconoir.css"

ICON_CLASS_PATTERN = re.compile(r"iconoir-[a-z-]+")
# Upstream emits one rule per icon with no newline between rules, and the
# mask-image data URIs contain no braces, so a non-greedy brace match isolates
# a single rule.
ICON_RULE_PATTERN = re.compile(r"\.(iconoir-[a-z0-9-]+)::before\{[^}]*\}")


def _rules_by_class(css_text):
    matches = ICON_RULE_PATTERN.finditer(css_text)
    return {match.group(1): match.group(0) for match in matches}


class TestIconoirSubsetContract(SimpleTestCase):
    def setUp(self):
        # Same scope as scripts/vendor_assets.sh: every app-authored script and
        # every template, so an icon added outside main.js is still vendored.
        self.icon_sources = sorted(
            [*STATIC_DIR.glob("*.js"), *TEMPLATES_DIR.glob("*.html")]
        )
        self.used_icon_classes = set()
        for path in self.icon_sources:
            self.used_icon_classes |= set(ICON_CLASS_PATTERN.findall(path.read_text()))

        self.iconoir_css = ICONOIR_CSS_PATH.read_text()
        self.vendored_rules = _rules_by_class(self.iconoir_css)
        self.defined_icon_classes = set(self.vendored_rules)

    def test_scan_includes_every_script_that_renders_icons(self):
        """Guards the guard: the toast scripts render icons too."""
        for name in ("main.js", "resilientFetch.js", "uiErrors.js"):
            with self.subTest(script=name):
                self.assertIn(STATIC_DIR / name, self.icon_sources)
        self.assertIn(TEMPLATES_DIR / "index.html", self.icon_sources)

    def test_every_used_icon_class_has_a_mask_rule(self):
        missing = self.used_icon_classes - self.defined_icon_classes
        self.assertEqual(
            missing,
            set(),
            f"Icon class(es) used but not defined in {ICONOIR_CSS_PATH}: "
            f"{sorted(missing)}. Add a .{{class}}::before mask-image rule "
            "copied from node_modules/iconoir/css/iconoir.css.",
        )

    def test_no_unused_icon_rules_are_vendored(self):
        """The subset exists to stay small, so stale rules are drift too."""
        unused = self.defined_icon_classes - self.used_icon_classes
        self.assertEqual(
            unused,
            set(),
            f"Icon rule(s) vendored but no longer used: {sorted(unused)}. "
            f"Remove them from {ICONOIR_CSS_PATH}.",
        )

    def test_at_least_one_icon_class_is_used(self):
        """Guards the guard: fails loudly if the scan itself finds nothing."""
        self.assertTrue(self.used_icon_classes)

    def test_vendored_rules_match_the_pinned_upstream_package(self):
        """Each vendored rule must be byte-identical to the pinned build.

        This is what makes the hand-copy step safe: an edited path, a stale
        glyph from an older Iconoir, or a rule assembled by hand instead of
        copied fails here rather than rendering a subtly wrong icon.
        """
        if not UPSTREAM_CSS_PATH.exists():
            self.skipTest(
                f"{UPSTREAM_CSS_PATH} not found; run `make packages-js` to "
                "check the vendored subset against the pinned package."
            )

        upstream_rules = _rules_by_class(UPSTREAM_CSS_PATH.read_text())

        for icon_class, vendored_rule in sorted(self.vendored_rules.items()):
            with self.subTest(icon_class=icon_class):
                self.assertIn(
                    icon_class,
                    upstream_rules,
                    f"{icon_class} is not in the pinned iconoir package. "
                    "Either the icon was renamed upstream or the pinned "
                    "version in package.json changed.",
                )
                self.assertEqual(
                    vendored_rule,
                    upstream_rules[icon_class],
                    f"The vendored rule for {icon_class} differs from the "
                    "pinned package. Re-copy it verbatim from "
                    f"{UPSTREAM_CSS_PATH}.",
                )

    def test_icon_elements_are_inline_block(self):
        """The <i class="iconoir-*"> element itself must be inline-block.

        Without this rule the element stays display: inline (the browser
        default for <i>), and its block-level ::before pseudo-element (set
        by the shared sizing rule) sits on the surrounding text's inline
        baseline rather than being centered against it, producing a visibly
        skewed/misaligned icon next to the text. Matches the upstream
        iconoir.css build, which carries this rule alongside the ::before
        sizing rule.
        """
        self.assertRegex(
            self.iconoir_css,
            r"\*\[class\^='iconoir-'\],\s*"
            r"\*\[class\*=' iconoir-'\]\s*\{\s*"
            r"display:\s*inline-block;?\s*\}",
        )
