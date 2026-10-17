"""DOM contract test for the index page.

Renders `/` through the Django test client and asserts that every element id,
class, and data-* attribute actually read by `main.js` or `tests/javascript/`
is present in the rendered markup, plus the CSS keyframe names `main.js`
assigns as animation strings.

Every theme is only a stylesheet applied to this one template, so these
hooks are the interface between the markup, main.js, and every theme. None
of them may move, be renamed, or disappear when a stylesheet changes or a
theme is added.

The page also must not carry the unused layout wrappers `#top-bar`,
`#top-left-box`, `#top-center-box`, and `#top-right-box`. Nothing in
JavaScript reads them, and a theme that relied on them for inherited styles
would break in any template that omits them, so their absence is asserted.
"""

import re

from django.test import TestCase

from smplfrm.models import Config

# Element ids read by main.js via getElementById/querySelector, or asserted
# directly in tests/javascript/*.js against the real template markup.
EXPECTED_IDS = [
    "image-container",
    "progress-bar",
    "photo-date",
    "photo-date-group",
    "current-date",
    "current-date-group",
    "current-time",
    "current-time-group",
    "weather-group",
    "weather-temp",
    "bottom-bar",
    "spotify-bar",
    "spotify-now-playing",
    "logo-icon",
    "settings-modal",
    "close-modal",
    "cancel-settings",
    "save-settings",
    "error-message",
    "main-actions",
    "setting-date",
    "setting-force-date-path",
    "setting-clock",
    "setting-timezone",
    "setting-theme",
    "setting-refresh",
    "setting-transition",
    "setting-zoom",
    "setting-transition-type",
    "setting-fill-mode",
    "setting-cache-timeout",
    "tab-display",
    "tab-presets",
    "tab-plugins",
    "tab-tasks",
    "preset-list-body",
    "preset-page-prev",
    "preset-page-next",
    "preset-page-info",
    "plugin-list-view",
    "plugin-list-body",
    "plugin-page-prev",
    "plugin-page-next",
    "plugin-page-info",
    "plugin-detail-view",
    "plugin-detail-name",
    "plugin-detail-form",
    "plugin-detail-save",
    "plugin-detail-back",
    "plugin-detail-actions",
    "task-list-body",
    "task-page-prev",
    "task-page-next",
    "task-page-info",
    "task-reset-count",
    "task-clear-cache",
    "task-rescan-library",
    "task-toast",
    "task-toast-text",
    "task-toast-bar",
]

# Classes read by main.js via classList or querySelector(All).
EXPECTED_CLASSES = [
    "info-group",
    "group-separator",
    "tab-btn",
    "tab-content",
]

# data-* attributes read via element.dataset in main.js.
EXPECTED_DATA_ATTRS = [
    "data-config-id",
    "data-config-name",
    "data-tab",
]

# Keyframe names main.js assigns as animation strings in applyTransition()
# and fadeInImage(). Theme-neutral slideshow behaviour, not theme styling.
EXPECTED_KEYFRAMES = [
    "fadeIn",
    "slideInLeft",
    "slideInRight",
    "zoomInTransition",
    "zoomIn",
]


class TestIndexDomContract(TestCase):
    """Guards the DOM hooks that `main.js` and the JS suite rely on."""

    def setUp(self):
        Config.objects.all().delete()
        Config.objects.create(
            name="smplFrm Default",
            is_active=True,
            display_date=True,
            display_clock=True,
            image_refresh_interval=30000,
            image_transition_type="fade",
        )

    def test_expected_ids_present(self):
        response = self.client.get("/")
        content = response.content.decode()
        for element_id in EXPECTED_IDS:
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', content)

    def test_expected_classes_present(self):
        response = self.client.get("/")
        content = response.content.decode()
        for class_name in EXPECTED_CLASSES:
            with self.subTest(class_name=class_name):
                self.assertRegex(
                    content,
                    rf'class="[^"]*\b{re.escape(class_name)}\b[^"]*"',
                )

    def test_expected_data_attributes_present(self):
        response = self.client.get("/")
        content = response.content.decode()
        for attr in EXPECTED_DATA_ATTRS:
            with self.subTest(attr=attr):
                self.assertIn(attr, content)

    def test_keyframes_present_in_shipped_stylesheets(self):
        """The five slideshow keyframes exist in whatever stylesheet ships.

        Reads the static source file directly rather than fetching through
        the test client, since static assets are served by Whitenoise outside
        the Django test client's URL space in this project's configuration.
        """
        from pathlib import Path

        static_dir = Path(__file__).resolve().parent.parent.parent / "static"
        css_text = ""
        for css_file in static_dir.rglob("*.css"):
            css_text += css_file.read_text()

        for keyframe in EXPECTED_KEYFRAMES:
            with self.subTest(keyframe=keyframe):
                self.assertIn(f"@keyframes {keyframe}", css_text)


class TestIndexSelfContainment(TestCase):
    """No runtime requests to third-party CDNs; every asset is self-hosted."""

    def setUp(self):
        Config.objects.all().delete()
        Config.objects.create(
            name="smplFrm Default",
            is_active=True,
            display_date=True,
            display_clock=True,
            image_refresh_interval=30000,
            image_transition_type="fade",
        )

    def test_no_cdn_references_in_rendered_page(self):
        response = self.client.get("/")
        content = response.content.decode()
        for forbidden in ("googleapis", "gstatic", "jsdelivr"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)


class TestIndexSharedMarkup(TestCase):
    """Guards the shared markup: no unused wrappers, well-formed theme-neutral hooks."""

    def setUp(self):
        Config.objects.all().delete()
        Config.objects.create(
            name="smplFrm Default",
            is_active=True,
            display_date=True,
            display_clock=True,
            image_refresh_interval=30000,
            image_transition_type="fade",
        )

    def test_unused_wrappers_absent(self):
        response = self.client.get("/")
        content = response.content.decode()
        for wrapper_id in (
            "top-bar",
            "top-left-box",
            "top-center-box",
            "top-right-box",
        ):
            with self.subTest(wrapper_id=wrapper_id):
                self.assertNotIn(f'id="{wrapper_id}"', content)

    def test_spotify_bar_is_not_self_closed(self):
        """The spotify-bar div must open and close separately.

        A self-closed `<div ... />` is parsed by browsers as an open tag,
        nesting the following `.info-group` inside it instead of beside it.
        """
        response = self.client.get("/")
        content = response.content.decode()
        self.assertNotIn('id="spotify-bar" style="display: none;" />', content)
        self.assertIn("</div>", content)


class TestIndexDialogSemantics(TestCase):
    """Guards theme-neutral accessibility: dialog semantics and labelling."""

    def setUp(self):
        Config.objects.all().delete()
        Config.objects.create(
            name="smplFrm Default",
            is_active=True,
            display_date=True,
            display_clock=True,
            image_refresh_interval=30000,
            image_transition_type="fade",
        )

    def test_settings_modal_has_dialog_role_and_accessible_name(self):
        response = self.client.get("/")
        content = response.content.decode()
        self.assertIn('role="dialog"', content)
        self.assertIn('aria-modal="true"', content)
        self.assertIn("aria-labelledby=", content)

    def test_logo_icon_is_a_real_button(self):
        """#logo-icon must be a <button>, not a styled <div>, for keyboard access."""
        response = self.client.get("/")
        content = response.content.decode()
        self.assertRegex(content, r'<button[^>]*id="logo-icon"')

    def test_icon_only_controls_have_aria_label(self):
        response = self.client.get("/")
        content = response.content.decode()
        logo_tag = re.search(r"<button[^>]*id=\"logo-icon\"[^>]*>", content).group(0)
        close_tag = re.search(r"<button[^>]*id=\"close-modal\"[^>]*>", content).group(0)
        self.assertIn("aria-label=", logo_tag)
        self.assertIn("aria-label=", close_tag)
