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
        self.assertEqual(response.data["task_type_label"], "Clear Cache")
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

    def test_list_tasks(self):
        """Test listing tasks returns non-deleted tasks."""
        response = self.client.get("/api/v1/tasks")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [t["id"] for t in response.data["results"]]
        self.assertIn(self.task.external_id, ids)

    def test_list_tasks_excludes_deleted(self):
        """Test that soft-deleted tasks are excluded from listing."""
        deleted_task = Task.objects.create(
            task_type=Task.TaskType.CLEAR_CACHE,
            status=Task.Status.COMPLETED,
            deleted=True,
        )
        response = self.client.get("/api/v1/tasks")
        ids = [t["id"] for t in response.data["results"]]
        self.assertNotIn(deleted_task.external_id, ids)
        self.assertIn(self.task.external_id, ids)

    def test_list_tasks_pagination_forward_and_backward(self):
        """Test pagination navigates forward and backward."""
        # Page size is 5; setUp already created 1 task, add 5 more for 6 total
        for i in range(5):
            Task.objects.create(
                task_type=Task.TaskType.CLEAR_CACHE,
                status=Task.Status.COMPLETED,
            )

        # Page 1
        response = self.client.get("/api/v1/tasks")
        self.assertEqual(response.data["count"], 6)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

        # Page 2 (forward)
        response = self.client.get("/api/v1/tasks?page=2")
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIsNone(response.data["next"])
        self.assertIsNotNone(response.data["previous"])

        # Back to page 1 (backward)
        response = self.client.get("/api/v1/tasks?page=1")
        self.assertEqual(len(response.data["results"]), 5)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

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

    def test_delete_task_soft_deletes(self):
        """Test that DELETE soft-deletes the task."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.task.refresh_from_db()
        self.assertTrue(self.task.deleted)

    def test_delete_task_excluded_from_list(self):
        """Test that a deleted task no longer appears in list."""
        self.client.delete(self.url)
        response = self.client.get("/api/v1/tasks")
        ids = [t["id"] for t in response.data["results"]]
        self.assertNotIn(self.task.external_id, ids)

    def test_delete_task_not_found_after_delete(self):
        """Test that GET returns 404 after soft-delete."""
        self.client.delete(self.url)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_task_dispatches_correct_celery_name(self):
        """Test that task creation sends the correct Celery task name."""
        from unittest.mock import patch

        with patch("smplfrm.celery.app") as mock_app:
            self.client.post(
                "/api/v1/tasks",
                {"task_type": "clear_cache"},
                format="json",
            )
            mock_app.send_task.assert_called_once()
            self.assertEqual(mock_app.send_task.call_args[0][0], "clear_cache")

    def test_create_task_conflict_when_pending(self):
        """Test that creating a task with same type already pending returns 409."""
        Task.objects.create(
            task_type=Task.TaskType.CLEAR_CACHE, status=Task.Status.PENDING
        )
        response = self.client.post(
            "/api/v1/tasks", {"task_type": "clear_cache"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_create_task_conflict_when_running(self):
        """Test that creating a task with same type already running returns 409."""
        Task.objects.create(
            task_type=Task.TaskType.CLEAR_CACHE, status=Task.Status.RUNNING
        )
        response = self.client.post(
            "/api/v1/tasks", {"task_type": "clear_cache"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_create_task_allowed_when_previous_completed(self):
        """Test that a new task is allowed when previous task of same type completed."""
        Task.objects.create(
            task_type=Task.TaskType.CLEAR_CACHE, status=Task.Status.COMPLETED
        )
        response = self.client.post(
            "/api/v1/tasks", {"task_type": "clear_cache"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_task_allowed_when_previous_failed(self):
        """Test that a new task is allowed when previous task of same type failed."""
        Task.objects.create(
            task_type=Task.TaskType.CLEAR_CACHE, status=Task.Status.FAILED
        )
        response = self.client.post(
            "/api/v1/tasks", {"task_type": "clear_cache"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_different_task_type_allowed(self):
        """Test that a different task type can be created while another is active."""
        Task.objects.create(
            task_type=Task.TaskType.CLEAR_CACHE, status=Task.Status.RUNNING
        )
        response = self.client.post(
            "/api/v1/tasks", {"task_type": "reset_image_count"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_all_task_types_dispatch_correctly(self):
        """Test that all task types map to correct Celery task names."""
        from smplfrm.views.api.v1.tasks import TASK_DISPATCH

        expected = {
            Task.TaskType.RESCAN_LIBRARY: "scan_library",
            Task.TaskType.RESET_IMAGE_COUNT: "reset_image_count",
            Task.TaskType.CLEAR_CACHE: "clear_cache",
        }
        self.assertEqual(TASK_DISPATCH, expected)
