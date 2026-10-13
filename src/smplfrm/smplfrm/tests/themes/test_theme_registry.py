"""Tests for the theme registry.

Mirrors the shape and testing style of smplfrm/tests/plugins/test_plugin_map.py.
"""

from django.contrib.staticfiles import finders
from django.test import TestCase

from smplfrm.themes import (
    DEFAULT_THEME_ID,
    THEME_REGISTRY,
    get_all_themes,
    get_theme_map,
    resolve,
)
from smplfrm.themes.classic import ClassicTheme


class TestThemeRegistry(TestCase):
    def test_registry_contains_classic(self):
        self.assertIn(ClassicTheme, THEME_REGISTRY)

    def test_default_theme_id_is_classic(self):
        self.assertEqual(DEFAULT_THEME_ID, "classic")


class TestGetAllThemes(TestCase):
    def test_returns_registry_declaration_order(self):
        themes = get_all_themes()
        ids = [theme.id for theme in themes]
        expected = [cls().id for cls in THEME_REGISTRY]
        self.assertEqual(ids, expected)

    def test_returns_theme_instances(self):
        themes = get_all_themes()
        for theme in themes:
            self.assertTrue(hasattr(theme, "id"))
            self.assertTrue(hasattr(theme, "label"))
            self.assertTrue(hasattr(theme, "description"))
            self.assertTrue(hasattr(theme, "stylesheet"))


class TestGetThemeMap(TestCase):
    def test_returns_dict_keyed_by_id(self):
        theme_map = get_theme_map()
        self.assertIn("classic", theme_map)

    def test_values_are_theme_instances(self):
        theme_map = get_theme_map()
        self.assertIsInstance(theme_map["classic"], ClassicTheme)


class TestResolve(TestCase):
    def test_resolve_known_id_returns_matching_theme(self):
        theme = resolve("classic")
        self.assertEqual(theme.id, "classic")

    def test_resolve_unknown_id_returns_default_and_logs(self):
        with self.assertLogs("smplfrm.themes", level="WARNING"):
            theme = resolve("not-a-real-theme")
        self.assertEqual(theme.id, DEFAULT_THEME_ID)

    def test_resolve_empty_string_returns_default_and_logs(self):
        with self.assertLogs("smplfrm.themes", level="WARNING"):
            theme = resolve("")
        self.assertEqual(theme.id, DEFAULT_THEME_ID)

    def test_resolve_none_returns_default_and_logs(self):
        with self.assertLogs("smplfrm.themes", level="WARNING"):
            theme = resolve(None)
        self.assertEqual(theme.id, DEFAULT_THEME_ID)


class TestThemeStylesheets(TestCase):
    """Every registered stylesheet must resolve to a file that exists.

    `resolve()` validates theme ids, not stylesheet paths, so a typo in a
    `Theme.stylesheet` surfaces only as a 404 on the rendered page with the
    frame drawn unstyled and no server-side signal. The path is also what
    `{% static %}` is handed directly in templates/index.html, so it has to
    be resolvable by the staticfiles finders.
    """

    def test_every_registered_stylesheet_exists(self):
        for theme in get_all_themes():
            with self.subTest(theme=theme.id):
                self.assertIsNotNone(
                    finders.find(theme.stylesheet),
                    f"Theme {theme.id!r} declares stylesheet "
                    f"{theme.stylesheet!r}, which no staticfiles finder can "
                    "resolve. Add the file under static/css/ or correct the "
                    "path in the Theme subclass.",
                )
