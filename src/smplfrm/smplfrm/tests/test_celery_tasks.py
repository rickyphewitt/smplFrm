"""Tests for Celery task registration and beat schedules.

Ensures all tasks are properly registered with Celery and discoverable
at runtime to prevent 'unregistered task' errors.
"""

from django.test import TestCase

from smplfrm.celery import app


class TestCeleryTaskRegistration(TestCase):
    """Test that all expected tasks are registered with Celery."""

    @classmethod
    def setUpClass(cls):
        """Import preload tasks to trigger registration."""
        super().setUpClass()
        # Import preload_tasks module to register tasks
        # This simulates what happens in production via worker_init signal
        import smplfrm.tasks.preload_tasks  # noqa: F401

    def test_preload_image_cache_task_registered(self):
        """Preload task must be registered to prevent runtime errors."""
        registered_tasks = list(app.tasks.keys())
        self.assertIn("preload_image_cache", registered_tasks)

    def test_recover_stale_preload_tasks_registered(self):
        """Stale recovery task must be registered for beat schedule."""
        registered_tasks = list(app.tasks.keys())
        self.assertIn("recover_stale_preload_tasks", registered_tasks)

    def test_clear_old_tasks_registered(self):
        """Clear old tasks must be registered for beat schedule."""
        registered_tasks = list(app.tasks.keys())
        self.assertIn("clear_old_tasks", registered_tasks)


class TestCeleryBeatSchedule(TestCase):
    """Test beat schedule configuration."""

    def test_recover_stale_preload_tasks_scheduled(self):
        """Stale recovery task must be in beat schedule."""
        beat_schedule = app.conf.beat_schedule
        self.assertIn("recover-stale-preload-tasks", beat_schedule)
        schedule_entry = beat_schedule["recover-stale-preload-tasks"]
        self.assertEqual(schedule_entry["task"], "recover_stale_preload_tasks")
        self.assertEqual(schedule_entry["schedule"], 300)  # 5 minutes

    def test_clear_old_tasks_scheduled(self):
        """Clear old tasks must be in beat schedule."""
        beat_schedule = app.conf.beat_schedule
        self.assertIn("clear-old-tasks", beat_schedule)
        schedule_entry = beat_schedule["clear-old-tasks"]
        self.assertEqual(schedule_entry["task"], "clear_old_tasks")
        # Schedule type varies (could be crontab or interval), just verify it exists
        self.assertIn("schedule", schedule_entry)
