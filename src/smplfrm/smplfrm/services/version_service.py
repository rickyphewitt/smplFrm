from pathlib import Path

from django.conf import settings

FALLBACK_VERSION = "unknown"


class VersionService:
    """Reads the application version from the VERSION file."""

    def __init__(self, version_file: Path = None):
        self._version_file = version_file or settings.PROJECT_ROOT / "VERSION"

    def get_version(self) -> str:
        """Return the version string from the VERSION file.

        Returns FALLBACK_VERSION if the file is missing or unreadable.
        """
        try:
            return self._version_file.read_text().strip()
        except (FileNotFoundError, PermissionError, OSError):
            return FALLBACK_VERSION
