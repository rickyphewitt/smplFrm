import os
import stat
import tempfile
from pathlib import Path

from django.test import TestCase

from smplfrm.services.version_service import FALLBACK_VERSION, VersionService


class TestVersionService(TestCase):
    """Tests for VersionService file reading and fallback behavior."""

    def test_read_tag_version(self):
        """Reading a file containing a tag version returns the tag string."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("v1.0.0")
            f.flush()
            path = Path(f.name)
        try:
            service = VersionService(version_file=path)
            self.assertEqual(service.get_version(), "v1.0.0")
        finally:
            path.unlink()

    def test_read_hash_version(self):
        """Reading a file containing a commit hash returns the hash string."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("abc1234")
            f.flush()
            path = Path(f.name)
        try:
            service = VersionService(version_file=path)
            self.assertEqual(service.get_version(), "abc1234")
        finally:
            path.unlink()

    def test_fallback_when_file_missing(self):
        """Returns fallback 'unknown' when the VERSION file does not exist."""
        missing_path = Path(tempfile.gettempdir()) / "nonexistent_version_file"
        service = VersionService(version_file=missing_path)
        self.assertEqual(service.get_version(), FALLBACK_VERSION)

    def test_fallback_when_file_unreadable(self):
        """Returns fallback 'unknown' when the VERSION file has no read permission."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("v2.0.0")
            f.flush()
            path = Path(f.name)
        try:
            # Remove all permissions
            os.chmod(path, 0o000)
            service = VersionService(version_file=path)
            self.assertEqual(service.get_version(), FALLBACK_VERSION)
        finally:
            # Restore permissions so cleanup can delete the file
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            path.unlink()

    def test_whitespace_is_stripped(self):
        """Leading and trailing whitespace is stripped from the version string."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("  v1.2.3\n  ")
            f.flush()
            path = Path(f.name)
        try:
            service = VersionService(version_file=path)
            self.assertEqual(service.get_version(), "v1.2.3")
        finally:
            path.unlink()

    def test_empty_file_returns_empty_string(self):
        """An empty VERSION file returns an empty string (not fallback)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")
            f.flush()
            path = Path(f.name)
        try:
            service = VersionService(version_file=path)
            self.assertEqual(service.get_version(), "")
        finally:
            path.unlink()
