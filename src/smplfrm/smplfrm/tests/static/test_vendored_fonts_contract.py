"""Contract test for the vendored theme font faces under static/fonts/.

Fonts are copied from pinned npm packages by scripts/vendor_assets.sh and
committed, because the runtime image ships no node_modules. Guarded here:

1. Shape: each family directory holds only Latin woff2 faces plus the
   family's license, and the license is the SIL Open Font License.
2. Fidelity: each face is byte-identical to the file in the pinned package.
   Runs only when node_modules is present and is skipped otherwise, so the
   suite stays runnable without a JavaScript toolchain.
3. Preloads: every font a registered theme asks the page to preload exists
   and is a woff2, since the template emits `type="font/woff2"`.
"""

from pathlib import Path

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase

from smplfrm.themes import get_all_themes

APP_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = APP_DIR.parent.parent.parent
FONTS_DIR = APP_DIR / "static" / "fonts"
NODE_FONTSOURCE_DIR = REPO_ROOT / "node_modules" / "@fontsource"


def _family_dirs():
    return sorted(path for path in FONTS_DIR.iterdir() if path.is_dir())


class TestVendoredFontsContract(SimpleTestCase):
    def setUp(self):
        self.family_dirs = _family_dirs()
        self.faces = sorted(FONTS_DIR.glob("*/*.woff2"))

    def test_at_least_one_family_is_vendored(self):
        """Guards the guard: fails loudly if the scan itself finds nothing."""
        self.assertTrue(self.family_dirs)
        self.assertTrue(self.faces)

    def test_each_family_holds_only_latin_woff2_faces_and_a_license(self):
        for family_dir in self.family_dirs:
            with self.subTest(family=family_dir.name):
                for path in family_dir.iterdir():
                    if path.name == "LICENSE":
                        continue
                    self.assertEqual(path.suffix, ".woff2", path.name)
                    self.assertTrue(
                        path.name.startswith(f"{family_dir.name}-latin-"),
                        f"{path.name} is not a Latin subset of {family_dir.name}",
                    )

    def test_each_family_ships_its_ofl_license(self):
        for family_dir in self.family_dirs:
            with self.subTest(family=family_dir.name):
                license_path = family_dir / "LICENSE"
                self.assertTrue(license_path.is_file(), f"{license_path} missing")
                self.assertIn(
                    "SIL Open Font License, Version 1.1",
                    license_path.read_text(),
                )

    def test_faces_match_the_pinned_packages(self):
        if not NODE_FONTSOURCE_DIR.exists():
            self.skipTest(
                f"{NODE_FONTSOURCE_DIR} not found; run `make packages-js` to "
                "check the vendored fonts against the pinned packages."
            )
        for face in self.faces:
            with self.subTest(face=face.name):
                upstream = NODE_FONTSOURCE_DIR / face.parent.name / "files" / face.name
                self.assertTrue(
                    upstream.is_file(),
                    f"{face.name} is not in @fontsource/{face.parent.name}. "
                    "Check FONT_FACES in scripts/vendor_assets.sh.",
                )
                self.assertEqual(
                    face.read_bytes(),
                    upstream.read_bytes(),
                    f"{face.name} differs from the pinned package. Re-run "
                    "`make vendor-assets`.",
                )


class TestThemePreloadFonts(SimpleTestCase):
    def test_every_preloaded_font_exists_and_is_woff2(self):
        for theme in get_all_themes():
            for font in theme.preload_fonts:
                with self.subTest(theme=theme.id, font=font):
                    self.assertTrue(font.endswith(".woff2"))
                    self.assertIsNotNone(
                        finders.find(font),
                        f"Theme {theme.id!r} preloads {font!r}, which no "
                        "staticfiles finder can resolve.",
                    )
