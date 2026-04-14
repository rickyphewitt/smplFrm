"""
Tests for boolean environment variable parsing in settings.py.

Verifies that falsy string values ("False", "0", "no") correctly evaluate
to False, truthy strings ("True") evaluate to True, defaults are preserved
when env vars are unset, and non-boolean settings remain unchanged.
"""

import importlib
import os
from unittest.mock import patch

import pytest

AFFECTED_SETTINGS = [
    "SMPL_FRM_DISPLAY_DATE",
    "SMPL_FRM_FORCE_DATE_FROM_PATH",
    "SMPL_FRM_DISPLAY_CLOCK",
    "SMPL_FRM_IMAGE_ZOOM_EFFECT",
]

FALSY_STRINGS = ["False", "false", "FALSE", "0", "no", "No", "NO"]


def _reload_settings():
    """Reload the settings module so patched env vars take effect."""
    import smplfrm.settings as settings_module

    return importlib.reload(settings_module)


class TestBugConditionExploration:
    """Falsy string values should evaluate to False for boolean settings."""

    def test_display_date_false_string(self):
        """SMPL_FRM_DISPLAY_DATE set to 'False' should be False."""
        with patch.dict(os.environ, {"SMPL_FRM_DISPLAY_DATE": "False"}):
            settings = _reload_settings()
            assert settings.SMPL_FRM_DISPLAY_DATE is False

    def test_display_clock_zero_string(self):
        """SMPL_FRM_DISPLAY_CLOCK set to '0' should be False."""
        with patch.dict(os.environ, {"SMPL_FRM_DISPLAY_CLOCK": "0"}):
            settings = _reload_settings()
            assert settings.SMPL_FRM_DISPLAY_CLOCK is False

    def test_image_zoom_effect_no_string(self):
        """SMPL_FRM_IMAGE_ZOOM_EFFECT set to 'no' should be False."""
        with patch.dict(os.environ, {"SMPL_FRM_IMAGE_ZOOM_EFFECT": "no"}):
            settings = _reload_settings()
            assert settings.SMPL_FRM_IMAGE_ZOOM_EFFECT is False

    def test_force_date_from_path_no_uppercase(self):
        """SMPL_FRM_FORCE_DATE_FROM_PATH set to 'NO' should be False (case-insensitive)."""
        with patch.dict(os.environ, {"SMPL_FRM_FORCE_DATE_FROM_PATH": "NO"}):
            settings = _reload_settings()
            assert settings.SMPL_FRM_FORCE_DATE_FROM_PATH is False

    @pytest.mark.parametrize(
        "setting_name,falsy_value",
        [(setting, value) for setting in AFFECTED_SETTINGS for value in FALSY_STRINGS],
        ids=[
            f"{setting}-{value}"
            for setting in AFFECTED_SETTINGS
            for value in FALSY_STRINGS
        ],
    )
    def test_all_falsy_strings_across_settings(self, setting_name, falsy_value):
        """Every recognized falsy string should produce False for each boolean setting."""
        with patch.dict(os.environ, {setting_name: falsy_value}):
            settings = _reload_settings()
            actual = getattr(settings, setting_name)
            assert actual is False, (
                f"Bug confirmed: {setting_name}={falsy_value!r} → "
                f"bool({falsy_value!r}) = {actual}, expected False"
            )


# --- Preservation Tests ---
# These tests verify defaults, truthy parsing, and non-boolean settings.

TRUTHY_STRINGS = ["True", "true", "TRUE"]

# These were previously considered truthy but now only "true" is truthy
NON_TRUE_STRINGS = ["1", "yes", "Yes", "YES", "0", "no", "No", "NO", "maybe", ""]

NON_BOOLEAN_SETTINGS_DEFAULTS = {
    "SMPL_FRM_EXTERNAL_PORT": 8321,
    "SMPL_FRM_HOST": "localhost",
    "SMPL_FRM_PROTOCOL": "http://",
    "SMPL_FRM_IMAGE_REFRESH_INTERVAL": 30000,
    "SMPL_FRM_IMAGE_TRANSITION_INTERVAL": 10000,
    "SMPL_FRM_IMAGE_CACHE_TIMEOUT": 300,
    "SMPL_FRM_TIMEZONE": "America/Los_Angeles",
    "SMPL_FRM_IMAGE_FILL_MODE": "blur",
    "SMPL_FRM_IMAGE_TRANSITION_TYPE": "random",
}

# List-type settings checked separately (they are lists, not scalars)
NON_BOOLEAN_LIST_SETTINGS = [
    "SMPL_FRM_LIBRARY_DIRS",
    "SMPL_FRM_IMAGE_FORMATS",
]


class TestPreservationDefaults:
    """When no boolean env vars are set, all four default to True."""

    @pytest.mark.parametrize("setting_name", AFFECTED_SETTINGS)
    def test_boolean_defaults_are_true(self, setting_name):
        """When the boolean env var is NOT set, the setting defaults to True."""
        env_patch = {k: v for k, v in os.environ.items() if k != setting_name}
        with patch.dict(os.environ, env_patch, clear=True):
            settings = _reload_settings()
            actual = getattr(settings, setting_name)
            assert (
                actual is True
            ), f"{setting_name} should default to True when unset, got {actual!r}"

    def test_all_boolean_defaults_true_simultaneously(self):
        """When ALL four boolean env vars are unset, they all default to True."""
        env_without_bools = {
            k: v for k, v in os.environ.items() if k not in AFFECTED_SETTINGS
        }
        with patch.dict(os.environ, env_without_bools, clear=True):
            settings = _reload_settings()
            for setting_name in AFFECTED_SETTINGS:
                actual = getattr(settings, setting_name)
                assert (
                    actual is True
                ), f"{setting_name} should default to True, got {actual!r}"


class TestPreservationTruthyStrings:
    """Only "true" (case-insensitive) produces True; all other strings produce False."""

    @pytest.mark.parametrize(
        "setting_name,truthy_value",
        [(setting, value) for setting in AFFECTED_SETTINGS for value in TRUTHY_STRINGS],
        ids=[
            f"{setting}-{value}"
            for setting in AFFECTED_SETTINGS
            for value in TRUTHY_STRINGS
        ],
    )
    def test_true_string_produces_true(self, setting_name, truthy_value):
        """Only 'true' (case-insensitive) should evaluate to True."""
        with patch.dict(os.environ, {setting_name: truthy_value}):
            settings = _reload_settings()
            actual = getattr(settings, setting_name)
            assert (
                actual is True
            ), f"{setting_name}={truthy_value!r} should be True, got {actual!r}"

    @pytest.mark.parametrize(
        "setting_name,non_true_value",
        [
            (setting, value)
            for setting in AFFECTED_SETTINGS
            for value in NON_TRUE_STRINGS
        ],
        ids=[
            f"{setting}-{value!r}"
            for setting in AFFECTED_SETTINGS
            for value in NON_TRUE_STRINGS
        ],
    )
    def test_non_true_strings_produce_false(self, setting_name, non_true_value):
        """Any string that isn't 'true' (case-insensitive) should be False."""
        with patch.dict(os.environ, {setting_name: non_true_value}):
            settings = _reload_settings()
            actual = getattr(settings, setting_name)
            assert (
                actual is False
            ), f"{setting_name}={non_true_value!r} should be False, got {actual!r}"


class TestPreservationNonBooleanSettings:
    """Non-boolean settings are parsed with their existing logic and remain unchanged."""

    def test_scalar_non_boolean_defaults(self):
        """Non-boolean scalar settings have correct default values."""
        env_clean = {
            k: v for k, v in os.environ.items() if not k.startswith("SMPL_FRM_")
        }
        with patch.dict(os.environ, env_clean, clear=True):
            settings = _reload_settings()
            for setting_name, expected in NON_BOOLEAN_SETTINGS_DEFAULTS.items():
                actual = getattr(settings, setting_name)
                assert (
                    actual == expected
                ), f"{setting_name} should be {expected!r}, got {actual!r}"

    def test_library_dirs_is_list(self):
        """SMPL_FRM_LIBRARY_DIRS defaults to a list (split by comma)."""
        env_clean = {
            k: v for k, v in os.environ.items() if not k.startswith("SMPL_FRM_")
        }
        with patch.dict(os.environ, env_clean, clear=True):
            settings = _reload_settings()
            assert isinstance(settings.SMPL_FRM_LIBRARY_DIRS, list)

    def test_image_formats_default(self):
        """SMPL_FRM_IMAGE_FORMATS defaults to ['jpg', 'png']."""
        env_clean = {
            k: v for k, v in os.environ.items() if not k.startswith("SMPL_FRM_")
        }
        with patch.dict(os.environ, env_clean, clear=True):
            settings = _reload_settings()
            assert settings.SMPL_FRM_IMAGE_FORMATS == ["jpg", "png"]

    def test_integer_settings_are_ints(self):
        """Integer non-boolean settings are parsed as int."""
        env_clean = {
            k: v for k, v in os.environ.items() if not k.startswith("SMPL_FRM_")
        }
        with patch.dict(os.environ, env_clean, clear=True):
            settings = _reload_settings()
            assert isinstance(settings.SMPL_FRM_EXTERNAL_PORT, int)
            assert isinstance(settings.SMPL_FRM_IMAGE_REFRESH_INTERVAL, int)
            assert isinstance(settings.SMPL_FRM_IMAGE_TRANSITION_INTERVAL, int)
            assert isinstance(settings.SMPL_FRM_IMAGE_CACHE_TIMEOUT, int)

    def test_string_settings_are_strings(self):
        """String non-boolean settings are plain strings."""
        env_clean = {
            k: v for k, v in os.environ.items() if not k.startswith("SMPL_FRM_")
        }
        with patch.dict(os.environ, env_clean, clear=True):
            settings = _reload_settings()
            assert isinstance(settings.SMPL_FRM_HOST, str)
            assert isinstance(settings.SMPL_FRM_PROTOCOL, str)
            assert isinstance(settings.SMPL_FRM_TIMEZONE, str)
            assert isinstance(settings.SMPL_FRM_IMAGE_FILL_MODE, str)
            assert isinstance(settings.SMPL_FRM_IMAGE_TRANSITION_TYPE, str)
