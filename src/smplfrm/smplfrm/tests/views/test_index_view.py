from unittest.mock import patch

from django.test import TestCase

import smplfrm.themes as themes
from smplfrm.models import Config
from smplfrm.themes.base import Theme
from smplfrm.themes.classic import ClassicTheme


class _PreloadingTheme(Theme):
    def __init__(self):
        super().__init__(
            id="preloading",
            label="Preloading",
            description="Declares two preload fonts",
            stylesheet="css/base.css",
            preload_fonts=(
                "fonts/geist/geist-latin-400-normal.woff2",
                "fonts/geist/geist-latin-500-normal.woff2",
            ),
        )


class TestIndexViewVersionContext(TestCase):
    """Tests that IndexView passes version from VersionService to template context."""

    def setUp(self):
        """Ensure an active config exists so IndexView renders without error."""
        Config.objects.all().delete()
        Config.objects.create(
            name="smplFrm Default",
            is_active=True,
            display_date=True,
            display_clock=True,
            image_refresh_interval=30000,
            image_transition_type="fade",
        )

    @patch("smplfrm.services.version_service.VersionService.get_version")
    def test_version_key_present_in_context(self, mock_get_version):
        """Template context includes the 'version' key."""
        mock_get_version.return_value = "v1.0.0"
        response = self.client.get("/")
        self.assertIn("version", response.context)

    @patch("smplfrm.services.version_service.VersionService.get_version")
    def test_version_value_comes_from_version_service(self, mock_get_version):
        """The version context value is the return value of VersionService.get_version()."""
        mock_get_version.return_value = "test-sentinel"
        response = self.client.get("/")
        self.assertEqual(response.context["version"], "test-sentinel")
        mock_get_version.assert_called_once()

    @patch("smplfrm.services.version_service.VersionService.get_version")
    def test_version_with_tag(self, mock_get_version):
        """When VersionService returns a tag version, context reflects it."""
        mock_get_version.return_value = "v2.3.1"
        response = self.client.get("/")
        self.assertEqual(response.context["version"], "v2.3.1")

    @patch("smplfrm.services.version_service.VersionService.get_version")
    def test_version_with_hash(self, mock_get_version):
        """When VersionService returns a commit hash, context reflects it."""
        mock_get_version.return_value = "abc1234"
        response = self.client.get("/")
        self.assertEqual(response.context["version"], "abc1234")

    @patch("smplfrm.services.version_service.VersionService.get_version")
    def test_version_unknown(self, mock_get_version):
        """When VersionService returns 'unknown', context reflects it."""
        mock_get_version.return_value = "unknown"
        response = self.client.get("/")
        self.assertEqual(response.context["version"], "unknown")


class TestIndexViewVersionTemplateRendering(TestCase):
    """Tests that the About tab renders version with correct links based on version type."""

    def setUp(self):
        """Ensure an active config exists so IndexView renders without error."""
        Config.objects.all().delete()
        Config.objects.create(
            name="smplFrm Default",
            is_active=True,
            display_date=True,
            display_clock=True,
            image_refresh_interval=30000,
            image_transition_type="fade",
        )

    @patch("smplfrm.services.version_service.VersionService.get_version")
    def test_tag_version_renders_as_release_link(self, mock_get_version):
        """A tag version (starts with 'v') renders as a GitHub release link."""
        mock_get_version.return_value = "v1.0.0"
        response = self.client.get("/")
        content = response.content.decode()
        self.assertIn(
            'href="https://github.com/rickyphewitt/smplFrm/releases/tag/v1.0.0"',
            content,
        )
        self.assertIn("v1.0.0", content)

    @patch("smplfrm.services.version_service.VersionService.get_version")
    def test_hash_version_renders_as_commit_link(self, mock_get_version):
        """A hash version renders as a GitHub commit link."""
        mock_get_version.return_value = "abc1234"
        response = self.client.get("/")
        content = response.content.decode()
        self.assertIn(
            'href="https://github.com/rickyphewitt/smplFrm/commit/abc1234"',
            content,
        )
        self.assertIn("abc1234", content)

    @patch("smplfrm.services.version_service.VersionService.get_version")
    def test_unknown_version_renders_as_plain_text(self, mock_get_version):
        """The 'unknown' version renders as plain text with no version link."""
        mock_get_version.return_value = "unknown"
        response = self.client.get("/")
        content = response.content.decode()
        self.assertIn("unknown", content)
        self.assertNotIn("releases/tag/unknown", content)
        self.assertNotIn("commit/unknown", content)

    @patch("smplfrm.services.version_service.VersionService.get_version")
    def test_tag_version_link_opens_in_new_tab(self, mock_get_version):
        """Release links have target='_blank' and rel='noopener noreferrer'."""
        mock_get_version.return_value = "v2.0.0"
        response = self.client.get("/")
        content = response.content.decode()
        self.assertIn('target="_blank"', content)
        self.assertIn('rel="noopener noreferrer"', content)
        self.assertIn(
            'href="https://github.com/rickyphewitt/smplFrm/releases/tag/v2.0.0"',
            content,
        )

    @patch("smplfrm.services.version_service.VersionService.get_version")
    def test_hash_version_link_opens_in_new_tab(self, mock_get_version):
        """Commit links have target='_blank' and rel='noopener noreferrer'."""
        mock_get_version.return_value = "def5678"
        response = self.client.get("/")
        content = response.content.decode()
        self.assertIn('target="_blank"', content)
        self.assertIn('rel="noopener noreferrer"', content)
        self.assertIn(
            'href="https://github.com/rickyphewitt/smplFrm/commit/def5678"',
            content,
        )


class TestIndexViewAboutPageLinks(TestCase):
    """Tests that the About tab renders static links for GitHub and Wiki."""

    def setUp(self):
        """Ensure an active config exists so IndexView renders without error."""
        Config.objects.all().delete()
        Config.objects.create(
            name="smplFrm Default",
            is_active=True,
            display_date=True,
            display_clock=True,
            image_refresh_interval=30000,
            image_transition_type="fade",
        )

    @patch("smplfrm.services.version_service.VersionService.get_version")
    def test_github_repo_link_present(self, mock_get_version):
        """The About tab includes a link to the GitHub repository."""
        mock_get_version.return_value = "v1.0.0"
        response = self.client.get("/")
        content = response.content.decode()
        self.assertIn('href="https://github.com/rickyphewitt/smplFrm"', content)
        self.assertIn("rickyphewitt/smplFrm", content)

    @patch("smplfrm.services.version_service.VersionService.get_version")
    def test_wiki_link_present(self, mock_get_version):
        """The About tab includes a link to the GitHub wiki."""
        mock_get_version.return_value = "v1.0.0"
        response = self.client.get("/")
        content = response.content.decode()
        self.assertIn('href="https://github.com/rickyphewitt/smplFrm/wiki"', content)
        self.assertIn("smplFrm Wiki", content)

    @patch("smplfrm.services.version_service.VersionService.get_version")
    def test_static_links_open_in_new_tab(self, mock_get_version):
        """GitHub and Wiki links open in a new tab with noopener noreferrer."""
        mock_get_version.return_value = "v1.0.0"
        response = self.client.get("/")
        content = response.content.decode()
        # Find the GitHub link and verify attributes
        github_idx = content.index("rickyphewitt/smplFrm →")
        github_section = content[max(0, github_idx - 200) : github_idx]
        self.assertIn('target="_blank"', github_section)
        self.assertIn('rel="noopener noreferrer"', github_section)
        # Find the Wiki link and verify attributes
        wiki_idx = content.index("smplFrm Wiki")
        wiki_section = content[max(0, wiki_idx - 200) : wiki_idx]
        self.assertIn('target="_blank"', wiki_section)
        self.assertIn('rel="noopener noreferrer"', wiki_section)


class TestIndexViewThemeResolution(TestCase):
    """Tests that IndexView resolves the active config's theme into context."""

    def setUp(self):
        Config.objects.all().delete()

    def test_valid_theme_resolves_to_matching_stylesheet(self):
        """A config with a registered theme id resolves to that theme's stylesheet."""
        Config.objects.create(
            name="smplFrm Default",
            is_active=True,
            theme="classic",
        )
        response = self.client.get("/")
        self.assertEqual(response.context["theme_stylesheet"], "css/theme-classic.css")

    def test_invalid_theme_resolves_to_default_stylesheet(self):
        """A config with an unregistered theme id falls back to the default theme."""
        Config.objects.create(
            name="smplFrm Default",
            is_active=True,
            theme="not-a-real-theme",
        )
        response = self.client.get("/")
        self.assertEqual(response.context["theme_stylesheet"], "css/theme-classic.css")

    def test_page_never_renders_empty_stylesheet_href(self):
        """The rendered page never contains an empty or unresolved stylesheet href."""
        Config.objects.create(
            name="smplFrm Default",
            is_active=True,
            theme="not-a-real-theme",
        )
        response = self.client.get("/")
        content = response.content.decode()
        self.assertNotIn('href=""', content)


class TestIndexViewThemePreloadFonts(TestCase):
    """Tests that IndexView emits the active theme's font preloads."""

    def setUp(self):
        Config.objects.all().delete()

    def _preload_links(self, content):
        return [
            line.strip() for line in content.splitlines() if 'rel="preload"' in line
        ]

    def test_classic_renders_no_preload_links(self):
        Config.objects.create(name="smplFrm Default", is_active=True, theme="classic")
        response = self.client.get("/")
        self.assertEqual(response.context["theme_preload_fonts"], ())
        self.assertEqual(self._preload_links(response.content.decode()), [])

    @patch.object(themes, "THEME_REGISTRY", [ClassicTheme, _PreloadingTheme])
    def test_each_preload_font_renders_one_crossorigin_font_link(self):
        Config.objects.create(
            name="smplFrm Default", is_active=True, theme="preloading"
        )
        response = self.client.get("/")
        content = response.content.decode()

        links = self._preload_links(content)
        self.assertEqual(len(links), 2)
        for link, font in zip(links, _PreloadingTheme().preload_fonts):
            with self.subTest(font=font):
                self.assertIn(f"{font}", link)
                self.assertIn('as="font"', link)
                self.assertIn('type="font/woff2"', link)
                # Font preloads are always fetched in CORS mode; without
                # crossorigin the browser discards the preload and fetches twice.
                self.assertIn("crossorigin", link)

    @patch.object(themes, "THEME_REGISTRY", [ClassicTheme, _PreloadingTheme])
    def test_preloads_precede_the_stylesheets(self):
        Config.objects.create(
            name="smplFrm Default", is_active=True, theme="preloading"
        )
        content = self.client.get("/").content.decode()
        self.assertLess(
            content.index('rel="preload"'), content.index('rel="stylesheet"')
        )

    @patch.object(themes, "THEME_REGISTRY", [ClassicTheme, _PreloadingTheme])
    def test_unknown_theme_falls_back_to_default_preloads(self):
        Config.objects.create(name="smplFrm Default", is_active=True, theme="gone")
        response = self.client.get("/")
        self.assertEqual(response.context["theme_preload_fonts"], ())
