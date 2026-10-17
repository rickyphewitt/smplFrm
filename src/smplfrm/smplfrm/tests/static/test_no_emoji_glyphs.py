"""Guard against emoji in the shipped UI sources.

Icons are drawn with the vendored Iconoir subset so every theme controls
their color and size through CSS. An emoji renders in the platform's color
emoji font instead, which no stylesheet can recolor, and it looks different
on every OS. JavaScript must not pick icons per theme, so an emoji that slips
back into the shared sources shows up in every theme at once.

The scan covers app-authored JavaScript, theme and base stylesheets, and
templates. The vendored icon CSS is excluded: it is generated from the pinned
package and verified by its own contract test.
"""

import re
from pathlib import Path

from django.test import SimpleTestCase

APP_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"

# Emoji and pictograph blocks, plus the emoji presentation selector that turns
# an otherwise plain symbol into a color emoji. Ordinary typographic
# characters (arrows, multiplication sign, ellipsis) fall outside these
# ranges and stay allowed.
EMOJI_PATTERN = re.compile(
    "["
    "\U0001f000-\U0001faff"  # Mahjong through Symbols and Pictographs Ext-A
    "\u2300-\u23ff"  # Miscellaneous Technical (hourglass, stopwatch, ...)
    "\u2600-\u27bf"  # Miscellaneous Symbols and Dingbats
    "\u2b00-\u2bff"  # Miscellaneous Symbols and Arrows (stars, squares)
    "\ufe0f"  # Variation Selector-16, emoji presentation
    "]"
)


def _ui_source_files():
    return sorted(
        [
            *STATIC_DIR.glob("*.js"),
            *(STATIC_DIR / "css").glob("*.css"),
            *TEMPLATES_DIR.rglob("*.html"),
        ]
    )


def _emoji_occurrences(path):
    """Yield (line_number, codepoint) for every emoji character in path."""
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        for match in EMOJI_PATTERN.finditer(line):
            yield line_number, f"U+{ord(match.group()):04X}"


class TestNoEmojiGlyphs(SimpleTestCase):
    def setUp(self):
        self.source_files = _ui_source_files()

    def test_ui_sources_contain_no_emoji(self):
        offenders = [
            f"{path.relative_to(APP_DIR)}:{line_number} {codepoint}"
            for path in self.source_files
            for line_number, codepoint in _emoji_occurrences(path)
        ]
        self.assertEqual(
            offenders,
            [],
            "Emoji found in UI sources. Use an Iconoir glyph element "
            "(see setIconText() in main.js) and run `make vendor-assets`.",
        )

    def test_scan_covers_js_css_and_templates(self):
        """Guards the guard: fails loudly if a glob stops matching."""
        suffixes = {path.suffix for path in self.source_files}
        self.assertEqual(suffixes, {".js", ".css", ".html"})
        self.assertIn(STATIC_DIR / "main.js", self.source_files)
        self.assertIn(TEMPLATES_DIR / "index.html", self.source_files)

    def test_pattern_matches_known_emoji_and_spares_typography(self):
        """Pins the character ranges so a regex edit cannot hollow out the scan."""
        for emoji in (
            "📷",
            "📅",
            "🕐",
            "🌡",
            "⚠",
            "🔒",
            "📍",
            "🌐",
            "👁",
            "⏳",
            "\ufe0f",
        ):
            with self.subTest(emoji=emoji):
                self.assertRegex(emoji, EMOJI_PATTERN)
        for plain in ("→", "×", "…", "°", "—", "·"):
            with self.subTest(plain=plain):
                self.assertNotRegex(plain, EMOJI_PATTERN)
