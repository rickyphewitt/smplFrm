"""Tests for reading SECRET_KEY from the DJANGO_SECRET_KEY environment variable."""

import importlib
import os
from unittest.mock import patch

DEV_FALLBACK = "django-insecure-1s5!+gf*u0x34#3+@1w%=np!^1o_ee$@$!_j2c!uh!aidkr3ja"


def _reload_settings():
    """Reload the settings module so patched env vars take effect."""
    import smplfrm.settings as settings_module

    return importlib.reload(settings_module)


class TestSecretKeyFromEnv:
    """SECRET_KEY should be read from DJANGO_SECRET_KEY env var."""

    def test_uses_env_var_when_set(self):
        """When DJANGO_SECRET_KEY is set, SECRET_KEY uses that value."""
        with patch.dict(os.environ, {"DJANGO_SECRET_KEY": "my-production-key"}):
            settings = _reload_settings()
            assert settings.SECRET_KEY == "my-production-key"

    def test_falls_back_to_dev_default_when_unset(self):
        """When DJANGO_SECRET_KEY is not set, SECRET_KEY uses the dev fallback."""
        env_without = {k: v for k, v in os.environ.items() if k != "DJANGO_SECRET_KEY"}
        with patch.dict(os.environ, env_without, clear=True):
            settings = _reload_settings()
            assert settings.SECRET_KEY == DEV_FALLBACK
