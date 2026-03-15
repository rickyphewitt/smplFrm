from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from smplfrm.models import Task


class TestTaskAPI(TestCase):
    """Test suite for Task API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.task = Task.objects.create(
            task_type=Task.TaskType.RESCAN_LIBRARY,
            status=Task.Status.RUNNING,
            progress=50,
        )
        self.url = f"/api/v1/tasks/{self.task.external_id}"

    def test_create_task(self):
        """Test creating a task via POST."""
        response = self.client.post(
            "/api/v1/tasks",
            {"task_type": "clear_cache"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["task_type"], "clear_cache")
        self.assertEqual(response.data["status"], "pending")
        self.assertEqual(response.data["progress"], 0)

    def test_create_task_invalid_type(self):
        """Test creating a task with invalid type returns error."""
        response = self.client.post(
            "/api/v1/tasks",
            {"task_type": "invalid_type"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_task_status(self):
        """Test polling task status via GET."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.task.external_id)
        self.assertEqual(response.data["task_type"], "rescan_library")
        self.assertEqual(response.data["status"], "running")
        self.assertEqual(response.data["progress"], 50)

    def test_list_tasks_forbidden(self):
        """Test that listing tasks is forbidden."""
        response = self.client.get("/api/v1/tasks")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_task_forbidden(self):
        """Test that PUT is forbidden."""
        response = self.client.put(
            self.url, {"task_type": "clear_cache"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_task_forbidden(self):
        """Test that PATCH is forbidden."""
        response = self.client.patch(self.url, {"progress": 75}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_task_forbidden(self):
        """Test that DELETE is forbidden."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_task_dispatches_correct_celery_name(self):
        """Test that task creation sends the correct Celery task name."""
        from unittest.mock import patch

        with patch("smplfrm.celery.app") as mock_app:
            self.client.post(
                "/api/v1/tasks",
                {"task_type": "rescan_library"},
                format="json",
            )
            mock_app.send_task.assert_called_once()
            self.assertEqual(mock_app.send_task.call_args[0][0], "scan_library")

    def test_create_all_task_types_dispatch_correctly(self):
        """Test that all task types map to correct Celery task names."""
        from smplfrm.views.api.v1.tasks import TASK_DISPATCH

        expected = {
            Task.TaskType.RESCAN_LIBRARY: "scan_library",
            Task.TaskType.RESET_IMAGE_COUNT: "reset_image_count",
            Task.TaskType.CLEAR_CACHE: "clear_cache",
        }
        self.assertEqual(TASK_DISPATCH, expected)
