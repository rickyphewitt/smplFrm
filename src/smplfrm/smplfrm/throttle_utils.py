"""Utility functions for throttle rate configuration."""

import logging
import os

logger = logging.getLogger(__name__)

VALID_PERIODS = {"second", "minute", "hour", "day"}


def parse_throttle_rate(env_var: str, default: str) -> str:
    """Read a throttle rate from an environment variable and validate its format.

    Returns the environment variable value if it matches the format
    ``{positive_integer}/{period}`` where period is one of second, minute,
    hour, or day. If the variable is not set, returns the default silently.
    If the variable is set but invalid, returns the default and logs a warning.
    """
    value = os.getenv(env_var)

    if value is None:
        return default

    parts = value.strip().split("/")

    if len(parts) != 2:
        logger.warning(
            "Invalid throttle rate '%s' for %s, using default '%s'",
            value,
            env_var,
            default,
        )
        return default

    number_str, period = parts

    try:
        number = int(number_str)
    except ValueError:
        logger.warning(
            "Invalid throttle rate '%s' for %s, using default '%s'",
            value,
            env_var,
            default,
        )
        return default

    if number < 1:
        logger.warning(
            "Invalid throttle rate '%s' for %s, using default '%s'",
            value,
            env_var,
            default,
        )
        return default

    if period not in VALID_PERIODS:
        logger.warning(
            "Invalid throttle rate '%s' for %s, using default '%s'",
            value,
            env_var,
            default,
        )
        return default

    return value
