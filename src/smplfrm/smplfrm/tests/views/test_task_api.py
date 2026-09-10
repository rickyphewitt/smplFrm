"""Tests for Task API endpoints with JSON:API format.

Task types are expressed as the JSON:API type field:
- rescan_library_tasks
- reset_image_count_tasks
- clear_cache_tasks
"""

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

    def _build_create_payload(self, jsonapi_type):
        """Build a JSON:API create payload."""
        return {
            "data": {
                "type": jsonapi_type,
                "attributes": {},
            }
        }

    # --- List endpoint ---

    def test_list_returns_jsonapi_media_type(self):
        """Response Content-Type must be application/vnd.api+json."""
        response = self.client.get("/api/v1/tasks")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/vnd.api+json")

    def test_list_has_top_level_data_array(self):
        """List response must have top-level 'data' as an array."""
        response = self.client.get("/api/v1/tasks")
        data = response.json()

        self.assertIn("data", data)
        self.assertIsInstance(data["data"], list)

    def test_list_resources_have_type_and_id(self):
        """Each resource must have type and id fields."""
        response = self.client.get("/api/v1/tasks")
        data = response.json()

        for resource in data["data"]:
            self.assertIn("type", resource)
            self.assertIn("id", resource)

    def test_list_tasks(self):
        """Test listing tasks returns non-deleted tasks."""
        response = self.client.get("/api/v1/tasks")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        ids = [t["id"] for t in data["data"]]
        self.assertIn(self.task.external_id, ids)

    def test_list_tasks_excludes_deleted(self):
        """Test that soft-deleted tasks are excluded from listing."""
        deleted_task = Task.objects.create(
            task_type=Task.TaskType.CLEAR_CACHE,
            status=Task.Status.COMPLETED,
            deleted=True,
        )
        response = self.client.get("/api/v1/tasks")
        data = response.json()
        ids = [t["id"] for t in data["data"]]
        self.assertNotIn(deleted_task.external_id, ids)
        self.assertIn(self.task.external_id, ids)

    def test_list_tasks_pagination(self):
        """Test JSON:API pagination with page[number] and page[size]."""
        # Page size is 5; setUp already created 1 task, add 5 more for 6 total
        for i in range(5):
            Task.objects.create(
                task_type=Task.TaskType.CLEAR_CACHE,
                status=Task.Status.COMPLETED,
            )

        # Page 1
        response = self.client.get("/api/v1/tasks")
        data = response.json()
        self.assertEqual(data["meta"]["pagination"]["count"], 6)
        self.assertEqual(len(data["data"]), 5)
        self.assertIn("links", data)
        self.assertIsNotNone(data["links"].get("next"))

        # Page 2
        response = self.client.get("/api/v1/tasks?page[number]=2")
        data = response.json()
        self.assertEqual(len(data["data"]), 1)
        self.assertIsNone(data["links"].get("next"))
        self.assertIsNotNone(data["links"].get("prev"))

    # --- Detail endpoint ---

    def test_detail_returns_jsonapi_media_type(self):
        """Response Content-Type must be application/vnd.api+json."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/vnd.api+json")

    def test_detail_has_top_level_data_object(self):
        """Detail response must have top-level 'data' as an object."""
        response = self.client.get(self.url)
        data = response.json()

        self.assertIn("data", data)
        self.assertIsInstance(data["data"], dict)

    def test_get_task_status(self):
        """Test polling task status via GET."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["data"]["id"], self.task.external_id)
        self.assertEqual(data["data"]["type"], "rescan_library_tasks")
        self.assertEqual(data["data"]["attributes"]["status"], "running")
        self.assertEqual(data["data"]["attributes"]["progress"], 50)
        self.assertEqual(data["data"]["attributes"]["label"], "Rescan Library")

    def test_detail_nonexistent_returns_403(self):
        """GET for non-existent task returns 403 (enumeration prevention)."""
        response = self.client.get("/api/v1/tasks/nonexistent123")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Create endpoint ---

    def test_create_task(self):
        """Test creating a task via POST with JSON:API format."""
        response = self.client.post(
            "/api/v1/tasks",
            self._build_create_payload("clear_cache_tasks"),
            content_type="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["data"]["type"], "clear_cache_tasks")
        self.assertEqual(data["data"]["attributes"]["status"], "pending")
        self.assertEqual(data["data"]["attributes"]["progress"], 0)
        self.assertEqual(data["data"]["attributes"]["label"], "Clear Cache")

    def test_create_task_invalid_type(self):
        """Test creating a task with invalid type returns 409 Conflict."""
        response = self.client.post(
            "/api/v1/tasks",
            self._build_create_payload("invalid-type"),
            content_type="application/vnd.api+json",
        )

        # JSON:API spec: type mismatch is 409 Conflict
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_create_task_missing_type(self):
        """Test creating a task without type returns error."""
        response = self.client.post(
            "/api/v1/tasks",
            {"data": {"attributes": {}}},
            content_type="application/vnd.api+json",
        )

        # Parser rejects missing type as conflict
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_create_task_dispatches_correct_celery_name(self):
        """Test that task creation sends the correct Celery task name."""
        from unittest.mock import patch

        with patch("smplfrm.celery.app") as mock_app:
            self.client.post(
                "/api/v1/tasks",
                self._build_create_payload("clear_cache_tasks"),
                content_type="application/vnd.api+json",
            )
            mock_app.send_task.assert_called_once()
            self.assertEqual(mock_app.send_task.call_args[0][0], "clear_cache")

    def test_create_task_conflict_when_pending(self):
        """Test that creating a task with same type already pending returns 409."""
        Task.objects.create(
            task_type=Task.TaskType.CLEAR_CACHE, status=Task.Status.PENDING
        )
        response = self.client.post(
            "/api/v1/tasks",
            self._build_create_payload("clear_cache_tasks"),
            content_type="application/vnd.api+json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        data = response.json()
        self.assertIn("errors", data)
        self.assertEqual(data["errors"][0]["status"], "409")

    def test_create_task_conflict_when_running(self):
        """Test that creating a task with same type already running returns 409."""
        Task.objects.create(
            task_type=Task.TaskType.CLEAR_CACHE, status=Task.Status.RUNNING
        )
        response = self.client.post(
            "/api/v1/tasks",
            self._build_create_payload("clear_cache_tasks"),
            content_type="application/vnd.api+json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_create_task_allowed_when_previous_completed(self):
        """Test that a new task is allowed when previous task of same type completed."""
        Task.objects.create(
            task_type=Task.TaskType.CLEAR_CACHE, status=Task.Status.COMPLETED
        )
        response = self.client.post(
            "/api/v1/tasks",
            self._build_create_payload("clear_cache_tasks"),
            content_type="application/vnd.api+json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_task_allowed_when_previous_failed(self):
        """Test that a new task is allowed when previous task of same type failed."""
        Task.objects.create(
            task_type=Task.TaskType.CLEAR_CACHE, status=Task.Status.FAILED
        )
        response = self.client.post(
            "/api/v1/tasks",
            self._build_create_payload("clear_cache_tasks"),
            content_type="application/vnd.api+json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_different_task_type_allowed(self):
        """Test that a different task type can be created while another is active."""
        Task.objects.create(
            task_type=Task.TaskType.CLEAR_CACHE, status=Task.Status.RUNNING
        )
        response = self.client.post(
            "/api/v1/tasks",
            self._build_create_payload("reset_image_count_tasks"),
            content_type="application/vnd.api+json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_all_task_types(self):
        """Test that all task types can be created and return correct type."""
        type_mappings = [
            ("rescan_library_tasks", "Rescan Library"),
            ("reset_image_count_tasks", "Reset Image Count"),
            ("clear_cache_tasks", "Clear Cache"),
        ]

        for jsonapi_type, expected_label in type_mappings:
            # Clean up any conflicting tasks
            Task.objects.filter(
                status__in=[Task.Status.PENDING, Task.Status.RUNNING]
            ).update(status=Task.Status.COMPLETED)

            response = self.client.post(
                "/api/v1/tasks",
                self._build_create_payload(jsonapi_type),
                content_type="application/vnd.api+json",
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                f"Failed for {jsonapi_type}",
            )
            data = response.json()
            self.assertEqual(data["data"]["type"], jsonapi_type)
            self.assertEqual(data["data"]["attributes"]["label"], expected_label)

    def test_create_all_task_types_dispatch_correctly(self):
        """Test that all task types map to correct Celery task names."""
        from smplfrm.views.api.v1.tasks import TASK_DISPATCH

        expected = {
            Task.TaskType.RESCAN_LIBRARY: "scan_library",
            Task.TaskType.RESET_IMAGE_COUNT: "reset_image_count",
            Task.TaskType.CLEAR_CACHE: "clear_cache",
        }
        self.assertEqual(TASK_DISPATCH, expected)

    # --- Update/Patch endpoints ---

    def test_put_task_not_allowed(self):
        """Test that PUT returns 405 Method Not Allowed."""
        response = self.client.put(
            self.url,
            {"data": {"type": "rescan_library_tasks", "id": self.task.external_id}},
            content_type="application/vnd.api+json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        body = response.json()
        self.assertIn("errors", body)
        self.assertEqual(body["errors"][0]["status"], "405")

    def test_patch_task_not_allowed(self):
        """Test that PATCH returns 405 Method Not Allowed."""
        response = self.client.patch(
            self.url,
            {"data": {"type": "rescan_library_tasks", "id": self.task.external_id}},
            content_type="application/vnd.api+json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        body = response.json()
        self.assertIn("errors", body)
        self.assertEqual(body["errors"][0]["status"], "405")

    # --- Delete endpoint ---

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
        data = response.json()
        ids = [t["id"] for t in data["data"]]
        self.assertNotIn(self.task.external_id, ids)

    def test_delete_task_not_found_after_delete(self):
        """Test that GET returns 403 after soft-delete (enumeration prevention)."""
        self.client.delete(self.url)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_nonexistent_returns_403(self):
        """DELETE for non-existent task returns 403 (enumeration prevention)."""
        response = self.client.delete("/api/v1/tasks/nonexistent123")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
