"""Theme registry for smplFrm.

Mirrors the names and shape of smplfrm/plugins/__init__.py so the two read
alike. A theme is a named stylesheet, declared once in THEME_REGISTRY, and
resolve() is the only way the rest of the code turns a stored string into a
theme object. resolve() falls back to the default theme and logs a warning
for anything unknown, empty, or null, which is what lets a theme be deleted
later without a data migration.
"""

import logging

from smplfrm.themes.classic import ClassicTheme

logger = logging.getLogger(__name__)

THEME_REGISTRY = [ClassicTheme]

# Single source of truth for both the model field default and the resolve()
# fallback.
DEFAULT_THEME_ID = "classic"


def get_all_themes():
    """Return theme instances in registry declaration order."""
    return [cls() for cls in THEME_REGISTRY]


def get_theme_map():
    """Return a dict of theme instances keyed by id."""
    return {theme.id: theme for theme in get_all_themes()}


def resolve(theme_id):
    """Resolve a stored theme id into a Theme instance.

    Returns the default theme and logs a warning when theme_id is unknown,
    empty, or None. This is the single resolution point that allows a theme
    to be deleted later without breaking configs that still name it.
    """
    theme_map = get_theme_map()
    theme = theme_map.get(theme_id) if theme_id else None
    if theme is None:
        logger.warning(
            "Unknown theme id %r, falling back to default theme %r",
            theme_id,
            DEFAULT_THEME_ID,
        )
        return theme_map[DEFAULT_THEME_ID]
    return theme
