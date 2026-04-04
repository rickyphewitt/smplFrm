from django.test import TestCase
from unittest.mock import patch

from smplfrm.plugins.base import BasePlugin


class TestBasePluginOnSettingsChanged(TestCase):
    """BasePlugin.on_settings_changed() should be a no-op by default."""

    def test_on_settings_changed_default_noop(self):
        plugin = BasePlugin(name="test", description="Test plugin")
        # Should not raise
        plugin.on_settings_changed({"key": "value"})

    def test_on_settings_changed_returns_none(self):
        plugin = BasePlugin(name="test", description="Test plugin")
        result = plugin.on_settings_changed({"key": "value"})
        self.assertIsNone(result)

    @patch("smplfrm.plugins.base.BasePlugin.dispatch_task")
    def test_dispatch_task_sends_celery_task(self, mock_send):
        plugin = BasePlugin(name="test", description="Test plugin")
        plugin.dispatch_task("my_task")
        mock_send.assert_called_once_with("my_task")
