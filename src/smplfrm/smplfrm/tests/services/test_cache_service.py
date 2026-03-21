from django.test import TestCase
from django.test.utils import override_settings

from smplfrm.services import CacheService


class TestImageService(TestCase):
    def setUp(self):
        self.service = CacheService()
        self.cache_key = "randomHere"
        self.cache_data = {"some": "data"}

    def test_create_get_invalidate_cache_item(self):

        self.service.upsert(self.cache_key, self.cache_data)
        self.assertEqual(self.service.read(self.cache_key), self.cache_data)
        self.service.delete(self.cache_key)
        self.assertIsNone(self.service.read(self.cache_key))

    def test_configurable_cache_timeout(self):
        from smplfrm.models import Config

        config = None
        # get or create an active config
        configs = Config.objects.filter(is_active=True)
        if len(configs) > 0:
            config = configs[0]
            config.image_cache_timeout = 1
            config.save()
        else:
            config = Config.objects.create(image_cache_timeout=1, is_active=True)

        service = CacheService()
        service.upsert(self.cache_key, self.cache_data)
        from time import sleep

        sleep(2)
        self.assertIsNone(service.read(self.cache_key), self.cache_data)

    def test_upsert_uses_config_timeout(self):
        """Test that upsert reads timeout from Config model."""
        from smplfrm.models import Config

        Config.objects.create(image_cache_timeout=600)
        service = CacheService()
        service.upsert(self.cache_key, self.cache_data)
        # Data should still be present (600s timeout)
        self.assertEqual(service.read(self.cache_key), self.cache_data)

    def test_clear_cache(self):
        self.service.upsert(self.cache_key, self.cache_data)
        self.service.clear()
        self.assertIsNone(self.service.read(self.cache_key))

    def test_image_cache_key(self):
        ext_id = "foo"
        display_type = "blur"
        height = "10"
        width = "20"

        self.assertEqual(
            f"{ext_id}:{display_type}:{height}:{width}",
            self.service.get_image_cache_key(ext_id, height, width),
        )

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="border")
    def test_image_cache_key_with_different_fill_mode(self):
        ext_id = "foo"
        height = "10"
        width = "20"

        cache_key = self.service.get_image_cache_key(ext_id, height, width)
        self.assertEqual(f"{ext_id}:border:{height}:{width}", cache_key)

    @override_settings(SMPL_FRM_IMAGE_FILL_MODE="zoom_to_fill")
    def test_image_cache_key_dynamically_uses_setting(self):
        ext_id = "bar"
        height = "100"
        width = "200"

        cache_key = self.service.get_image_cache_key(ext_id, height, width)
        self.assertEqual(f"{ext_id}:zoom_to_fill:{height}:{width}", cache_key)

    def test_clear_calls_reporting_methods(self):
        """Test that clear calls initiate_task, report_task, and complete_task."""
        from unittest.mock import patch, call

        self.service.upsert(self.cache_key, self.cache_data)

        with patch.object(self.service, "initiate_task") as mock_init, patch.object(
            self.service, "report_task"
        ) as mock_report, patch.object(self.service, "complete_task") as mock_complete:
            self.service.clear(task_id="test-id")

            mock_init.assert_called_once_with("test-id", 1)
            mock_report.assert_called_once_with(1)
            mock_complete.assert_called_once()

    def test_clear_starts_task(self):
        """Test that task status is running during clear execution."""
        from unittest.mock import patch
        from smplfrm.models.task import Task, TaskType

        task = Task.objects.create(task_type=TaskType.CLEAR_CACHE)

        statuses = []
        with patch.object(
            self.service,
            "report_task",
            side_effect=lambda p: statuses.append(
                Task.objects.get(external_id=task.external_id).status
            ),
        ):
            self.service.clear(task_id=task.external_id)

        self.assertTrue(all(s == "running" for s in statuses))

    def test_clear_marks_failed_on_error(self):
        """Test that task is marked failed when clear encounters an error."""
        from unittest.mock import patch
        from smplfrm.models.task import Task, TaskType

        task = Task.objects.create(task_type=TaskType.CLEAR_CACHE)

        with patch.object(
            self.service.cache, "clear", side_effect=RuntimeError("cache error")
        ):
            with self.assertRaises(RuntimeError):
                self.service.clear(task_id=task.external_id)

        task.refresh_from_db()
        self.assertEqual(task.status, "failed")
        self.assertEqual(task.error, "cache error")
