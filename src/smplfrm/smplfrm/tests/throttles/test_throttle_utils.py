"""
Tests for throttle rate parsing utility.

Verifies that parse_throttle_rate correctly validates rate strings from
environment variables, returns valid rates unchanged, and falls back to
defaults with a warning log when values are invalid or missing.
"""

import logging
import os
from unittest.mock import patch

import pytest

from smplfrm.throttle_utils import parse_throttle_rate


class TestValidRates:
    """Valid rate strings should be returned unchanged."""

    @pytest.mark.parametrize(
        "rate",
        [
            "60/minute",
            "1/second",
            "500/hour",
            "10000/day",
        ],
        ids=["60-per-minute", "1-per-second", "500-per-hour", "10000-per-day"],
    )
    def test_valid_rate_returned_unchanged(self, rate):
        """A well-formed rate string is returned as-is."""
        with patch.dict(os.environ, {"TEST_RATE": rate}):
            result = parse_throttle_rate("TEST_RATE", "60/minute")
            assert result == rate

    def test_valid_rate_with_large_number(self):
        """Large positive integers are accepted."""
        with patch.dict(os.environ, {"TEST_RATE": "999999/day"}):
            result = parse_throttle_rate("TEST_RATE", "60/minute")
            assert result == "999999/day"

    def test_valid_rate_boundary_one(self):
        """The minimum valid number (1) is accepted for all periods."""
        for period in ("second", "minute", "hour", "day"):
            rate = f"1/{period}"
            with patch.dict(os.environ, {"TEST_RATE": rate}):
                result = parse_throttle_rate("TEST_RATE", "60/minute")
                assert result == rate


class TestInvalidRates:
    """Invalid rate strings should return the default and log a warning."""

    @pytest.mark.parametrize(
        "invalid_rate,description",
        [
            ("", "empty string"),
            ("60minute", "missing slash"),
            ("0/minute", "zero number"),
            ("-1/minute", "negative number"),
            ("60/weekly", "invalid period"),
            ("abc/minute", "non-numeric prefix"),
            ("60/minute/extra", "extra slashes"),
        ],
        ids=[
            "empty-string",
            "missing-slash",
            "zero-number",
            "negative-number",
            "invalid-period",
            "non-numeric-prefix",
            "extra-slashes",
        ],
    )
    def test_invalid_rate_returns_default(self, invalid_rate, description, caplog):
        """Invalid rate format falls back to default and logs a warning."""
        default = "120/minute"
        with patch.dict(os.environ, {"TEST_RATE": invalid_rate}):
            with caplog.at_level(logging.WARNING):
                result = parse_throttle_rate("TEST_RATE", default)
            assert result == default

    @pytest.mark.parametrize(
        "invalid_rate",
        [
            "",
            "60minute",
            "0/minute",
            "-1/minute",
            "60/weekly",
            "abc/minute",
            "60/minute/extra",
        ],
        ids=[
            "empty-string",
            "missing-slash",
            "zero-number",
            "negative-number",
            "invalid-period",
            "non-numeric-prefix",
            "extra-slashes",
        ],
    )
    def test_invalid_rate_logs_warning(self, invalid_rate, caplog):
        """Invalid rate values produce a warning log message."""
        with patch.dict(os.environ, {"TEST_RATE": invalid_rate}):
            with caplog.at_level(logging.WARNING):
                parse_throttle_rate("TEST_RATE", "60/minute")
            assert len(caplog.records) > 0
            assert caplog.records[0].levelno == logging.WARNING

    def test_float_number_is_invalid(self, caplog):
        """Decimal numbers are not valid (must be integer)."""
        with patch.dict(os.environ, {"TEST_RATE": "3.5/minute"}):
            with caplog.at_level(logging.WARNING):
                result = parse_throttle_rate("TEST_RATE", "60/minute")
            assert result == "60/minute"

    def test_whitespace_only_is_invalid(self, caplog):
        """Whitespace-only value is treated as invalid."""
        with patch.dict(os.environ, {"TEST_RATE": "   "}):
            with caplog.at_level(logging.WARNING):
                result = parse_throttle_rate("TEST_RATE", "60/minute")
            assert result == "60/minute"


class TestMissingEnvVar:
    """When the environment variable is not set, the default is returned."""

    def test_missing_env_var_returns_default(self):
        """Unset env var returns the provided default without logging."""
        env_without_key = {k: v for k, v in os.environ.items() if k != "TEST_RATE"}
        with patch.dict(os.environ, env_without_key, clear=True):
            result = parse_throttle_rate("TEST_RATE", "60/minute")
            assert result == "60/minute"

    def test_missing_env_var_does_not_log_warning(self, caplog):
        """Unset env var should not produce a warning (it's expected behavior)."""
        env_without_key = {k: v for k, v in os.environ.items() if k != "TEST_RATE"}
        with patch.dict(os.environ, env_without_key, clear=True):
            with caplog.at_level(logging.WARNING):
                parse_throttle_rate("TEST_RATE", "10/minute")
            warning_records = [
                r for r in caplog.records if r.levelno == logging.WARNING
            ]
            assert len(warning_records) == 0


class TestSettingsRestFrameworkConfig:
    """REST_FRAMEWORK settings dict contains correct throttle configuration."""

    def test_rest_framework_setting_exists(self, settings):
        """REST_FRAMEWORK dict is present in Django settings."""
        assert hasattr(settings, "REST_FRAMEWORK")
        assert isinstance(settings.REST_FRAMEWORK, dict)

    def test_default_throttle_classes_configured(self, settings):
        """DEFAULT_THROTTLE_CLASSES includes both global throttle classes."""
        rf = settings.REST_FRAMEWORK
        assert "DEFAULT_THROTTLE_CLASSES" in rf
        expected_classes = [
            "smplfrm.throttles.GlobalAnonThrottle",
            "smplfrm.throttles.GlobalAuthenticatedThrottle",
        ]
        assert rf["DEFAULT_THROTTLE_CLASSES"] == expected_classes

    def test_default_throttle_rates_contains_all_scopes(self, settings):
        """DEFAULT_THROTTLE_RATES has entries for anon, authenticated, and task scopes."""
        rf = settings.REST_FRAMEWORK
        assert "DEFAULT_THROTTLE_RATES" in rf
        rates = rf["DEFAULT_THROTTLE_RATES"]
        assert "global_anon" in rates
        assert "global_authenticated" in rates
        assert "global_task" in rates

    def test_default_throttle_rate_values(self, settings):
        """Default throttle rates match expected values when no env vars are set."""
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        assert rates["global_anon"] == "60/minute"
        assert rates["global_authenticated"] == "120/minute"
        assert rates["global_task"] == "10/minute"


class TestSettingsThrottleEnvOverrides:
    """Environment variables override default throttle rate values in settings."""

    def test_anon_rate_env_override(self, monkeypatch):
        """SMPL_FRM_THROTTLE_ANON_RATE env var overrides the anonymous rate."""
        monkeypatch.setenv("SMPL_FRM_THROTTLE_ANON_RATE", "30/hour")
        from smplfrm.throttle_utils import parse_throttle_rate

        result = parse_throttle_rate("SMPL_FRM_THROTTLE_ANON_RATE", "60/minute")
        assert result == "30/hour"

    def test_user_rate_env_override(self, monkeypatch):
        """SMPL_FRM_THROTTLE_USER_RATE env var overrides the authenticated rate."""
        monkeypatch.setenv("SMPL_FRM_THROTTLE_USER_RATE", "200/minute")
        from smplfrm.throttle_utils import parse_throttle_rate

        result = parse_throttle_rate("SMPL_FRM_THROTTLE_USER_RATE", "120/minute")
        assert result == "200/minute"

    def test_task_rate_env_override(self, monkeypatch):
        """SMPL_FRM_THROTTLE_TASK_RATE env var overrides the task creation rate."""
        monkeypatch.setenv("SMPL_FRM_THROTTLE_TASK_RATE", "5/minute")
        from smplfrm.throttle_utils import parse_throttle_rate

        result = parse_throttle_rate("SMPL_FRM_THROTTLE_TASK_RATE", "10/minute")
        assert result == "5/minute"

    def test_invalid_env_override_falls_back_to_default(self, monkeypatch, caplog):
        """Invalid env var value falls back to default rate."""
        monkeypatch.setenv("SMPL_FRM_THROTTLE_ANON_RATE", "invalid")
        from smplfrm.throttle_utils import parse_throttle_rate

        import logging

        with caplog.at_level(logging.WARNING):
            result = parse_throttle_rate("SMPL_FRM_THROTTLE_ANON_RATE", "60/minute")
        assert result == "60/minute"
