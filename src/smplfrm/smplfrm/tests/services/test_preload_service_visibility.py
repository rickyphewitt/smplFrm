from unittest.mock import patch

from django.test import TestCase

from smplfrm.models import Task
from smplfrm.services.preload_service import PreloadService
from smplfrm.tests.library_filter_fixtures import (
    activate_filter,
    make_image,
    set_filtering,
)


@patch("smplfrm.services.preload_service.app.send_task")
class TestPreloadServiceVisibility(TestCase):
    def setUp(self):
        self.service = PreloadService()
        self.framed = make_image("framed.jpg", tags=["frame"])
        self.plain = make_image("plain.jpg")
        set_filtering(True)
        activate_filter("frame")

    def test_hidden_images_are_dropped_from_the_batch(self, send_task):
        task = self.service.create_preload_task(
            [self.framed.external_id, self.plain.external_id], 100, 100
        )

        self.assertEqual(task.payload["image_ids"], [self.framed.external_id])
        send_task.assert_called_once()

    def test_batch_of_only_hidden_images_creates_no_task(self, send_task):
        with self.assertLogs("smplfrm.services.preload_service", "DEBUG") as logs:
            task = self.service.create_preload_task([self.plain.external_id], 100, 100)

        self.assertIsNone(task)
        self.assertFalse(Task.objects.exists())
        send_task.assert_not_called()
        self.assertTrue(any("hidden" in line for line in logs.output))
