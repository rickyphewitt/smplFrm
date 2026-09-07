"""Tests for Config API endpoints.

Endpoint: /api/v1/configs
- GET /configs - list all configs (paginated)
- GET /configs/{external_id} - config detail
- PUT /configs/{external_id} - full update of custom config
- DELETE /configs/{external_id} - delete custom config
- POST /configs/apply - create custom copy of active preset
- POST /configs/{external_id}/activate - activate a config

Resource type: configs
ID: external_id (16-char string)
Media type: application/vnd.api+json
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from smplfrm.models import Config


class TestConfigAPI(TestCase):
    """Test suite for Config API endpoints."""

    def setUp(self):
        self.client = APIClient()
        Config.objects.all().delete()
        self.config = Config.objects.create(
            name="smplFrm Default",
            description="All display elements enabled",
            is_active=True,
            display_date=True,
            display_clock=True,
            image_refresh_interval=30000,
            image_transition_type="fade",
        )
        self.url = f"/api/v1/configs/{self.config.external_id}"

    def _build_update_payload(self, config, **overrides):
        """Build a full JSON:API update payload with all attributes."""
        attrs = {
            "name": config.name,
            "description": config.description,
            "display_date": config.display_date,
            "display_clock": config.display_clock,
            "image_refresh_interval": config.image_refresh_interval,
            "image_transition_interval": config.image_transition_interval,
            "image_zoom_effect": config.image_zoom_effect,
            "image_transition_type": config.image_transition_type,
            "image_cache_timeout": config.image_cache_timeout,
            "image_fill_mode": config.image_fill_mode,
            "force_date_from_path": config.force_date_from_path,
            "timezone": config.timezone,
            "plugins": config.plugins,
            "is_active": config.is_active,
        }
        attrs.update(overrides)
        return {
            "data": {
                "type": "configs",
                "id": config.external_id,
                "attributes": attrs,
            }
        }

    # --- List endpoint ---

    def test_list_returns_jsonapi_media_type(self):
        """Response Content-Type must be application/vnd.api+json."""
        response = self.client.get("/api/v1/configs")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/vnd.api+json")

    def test_list_has_top_level_data_array(self):
        """List response must have top-level 'data' as an array."""
        response = self.client.get("/api/v1/configs")
        data = response.json()

        self.assertIn("data", data)
        self.assertIsInstance(data["data"], list)

    def test_list_resources_have_type_and_id(self):
        """Each resource must have type and id fields."""
        response = self.client.get("/api/v1/configs")
        data = response.json()

        for resource in data["data"]:
            self.assertIn("type", resource)
            self.assertIn("id", resource)
            self.assertEqual(resource["type"], "configs")
            self.assertIsInstance(resource["id"], str)
            self.assertEqual(len(resource["id"]), 16)

    def test_list_resources_have_attributes(self):
        """Each resource must have attributes with expected fields."""
        response = self.client.get("/api/v1/configs")
        data = response.json()

        for resource in data["data"]:
            self.assertIn("attributes", resource)
            attrs = resource["attributes"]
            self.assertIn("name", attrs)
            self.assertIn("description", attrs)
            self.assertIn("is_active", attrs)
            self.assertIn("display_date", attrs)
            self.assertIn("display_clock", attrs)

    def test_list_has_pagination_links(self):
        """List response must have pagination links."""
        response = self.client.get("/api/v1/configs")
        data = response.json()

        self.assertIn("links", data)
        links = data["links"]
        self.assertIn("first", links)
        self.assertIn("last", links)

    def test_list_has_pagination_meta(self):
        """List response must have pagination meta."""
        response = self.client.get("/api/v1/configs")
        data = response.json()

        self.assertIn("meta", data)
        meta = data["meta"]
        self.assertIn("pagination", meta)
        self.assertIn("count", meta["pagination"])

    def test_list_page_number_pagination(self):
        """Pagination uses page[number] query parameter."""
        for i in range(10):
            Config.objects.create(name=f"config{i}", is_active=False)

        response = self.client.get("/api/v1/configs?page[number]=2")
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("links", data)
        self.assertIn("prev", data["links"])

    def test_list_system_managed_first(self):
        """System-managed configs should appear before custom configs."""
        Config.objects.create(name="custom-20260101", is_active=False)
        Config.objects.create(name="smplFrm Minimal", is_active=False)

        response = self.client.get("/api/v1/configs")
        data = response.json()

        names = [r["attributes"]["name"] for r in data["data"]]
        smpl_names = [n for n in names if n.startswith("smplFrm")]
        custom_names = [n for n in names if not n.startswith("smplFrm")]
        self.assertEqual(names, smpl_names + custom_names)

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

    def test_detail_resource_has_correct_type_and_id(self):
        """Resource must have correct type and id."""
        response = self.client.get(self.url)
        data = response.json()

        self.assertEqual(data["data"]["type"], "configs")
        self.assertEqual(data["data"]["id"], self.config.external_id)

    def test_detail_includes_all_attributes(self):
        """Detail response must include all config attributes."""
        response = self.client.get(self.url)
        data = response.json()

        attrs = data["data"]["attributes"]
        self.assertEqual(attrs["name"], "smplFrm Default")
        self.assertEqual(attrs["description"], "All display elements enabled")
        self.assertTrue(attrs["is_active"])
        self.assertTrue(attrs["display_date"])
        self.assertTrue(attrs["display_clock"])
        self.assertEqual(attrs["image_refresh_interval"], 30000)
        self.assertEqual(attrs["image_transition_type"], "fade")

    def test_detail_not_found_returns_403(self):
        """Non-existent config returns 403 to prevent enumeration attacks."""
        response = self.client.get("/api/v1/configs/nonexistent12345")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Update endpoint ---

    def test_update_custom_config_with_put(self):
        """PUT request succeeds for custom config."""
        custom = Config.objects.create(
            name="custom-20260101",
            is_active=False,
            display_date=True,
            display_clock=True,
            image_refresh_interval=30000,
        )
        url = f"/api/v1/configs/{custom.external_id}"
        update_data = {
            "data": {
                "type": "configs",
                "id": custom.external_id,
                "attributes": {
                    "name": "custom-20260101",
                    "display_date": False,
                    "display_clock": False,
                    "image_refresh_interval": 60000,
                    "image_transition_interval": 5000,
                    "image_zoom_effect": False,
                    "image_transition_type": "zoom",
                    "image_cache_timeout": 600,
                },
            }
        }

        response = self.client.put(
            url, update_data, content_type="application/vnd.api+json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/vnd.api+json")

        data = response.json()
        attrs = data["data"]["attributes"]
        self.assertFalse(attrs["display_date"])
        self.assertFalse(attrs["display_clock"])
        self.assertEqual(attrs["image_refresh_interval"], 60000)
        self.assertEqual(attrs["image_transition_interval"], 5000)
        self.assertFalse(attrs["image_zoom_effect"])
        self.assertEqual(attrs["image_transition_type"], "zoom")
        self.assertEqual(attrs["image_cache_timeout"], 600)

        custom.refresh_from_db()
        self.assertFalse(custom.display_date)
        self.assertEqual(custom.image_refresh_interval, 60000)

    def test_update_managed_config_forbidden(self):
        """PUT on system-managed config with attribute changes returns 403."""
        update_data = {
            "data": {
                "type": "configs",
                "id": self.config.external_id,
                "attributes": {
                    "name": "smplFrm Default",
                    "display_date": False,  # Attempting to change attribute
                },
            }
        }

        response = self.client.put(
            self.url, update_data, content_type="application/vnd.api+json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_activate_system_managed_config(self):
        """PUT with is_active=true on system-managed config activates it."""
        # Create another managed config that's inactive
        other = Config.objects.create(name="smplFrm Minimal", is_active=False)
        update_data = self._build_update_payload(other, is_active=True)

        response = self.client.put(
            f"/api/v1/configs/{other.external_id}",
            update_data,
            content_type="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["data"]["attributes"]["is_active"])

        # Original active config should be deactivated
        self.config.refresh_from_db()
        self.assertFalse(self.config.is_active)

    def test_activate_already_active_config_is_noop(self):
        """PUT with is_active=true on already active config is a no-op."""
        update_data = self._build_update_payload(self.config, is_active=True)

        response = self.client.put(
            self.url, update_data, content_type="application/vnd.api+json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["data"]["attributes"]["is_active"])

    def test_update_with_wrong_content_type_rejected(self):
        """PUT with application/json should be rejected."""
        custom = Config.objects.create(name="custom-20260101", is_active=False)
        update_data = {"name": "custom-20260101", "display_date": False}

        response = self.client.put(
            f"/api/v1/configs/{custom.external_id}",
            update_data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_update_with_invalid_data(self):
        """Invalid data returns error."""
        custom = Config.objects.create(name="custom-20260101", is_active=False)
        update_data = {
            "data": {
                "type": "configs",
                "id": custom.external_id,
                "attributes": {
                    "name": "custom-20260101",
                    "image_refresh_interval": -1,
                },
            }
        }

        response = self.client.put(
            f"/api/v1/configs/{custom.external_id}",
            update_data,
            content_type="application/vnd.api+json",
        )

        self.assertNotEqual(response.status_code, status.HTTP_200_OK)

    def test_patch_forbidden(self):
        """PATCH for partial update should be forbidden."""
        patch_data = {
            "data": {
                "type": "configs",
                "id": self.config.external_id,
                "attributes": {"display_date": False},
            }
        }

        response = self.client.patch(
            self.url, patch_data, content_type="application/vnd.api+json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Delete endpoint ---

    def test_delete_custom_config_returns_204(self):
        """DELETE on custom config returns 204 and removes record."""
        custom = Config.objects.create(name="custom-20260101", is_active=False)
        ext_id = custom.external_id

        response = self.client.delete(f"/api/v1/configs/{ext_id}")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Config.objects.filter(external_id=ext_id).exists())

    def test_delete_managed_config_forbidden(self):
        """DELETE on system-managed config returns 403."""
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(
            Config.objects.filter(external_id=self.config.external_id).exists()
        )

    # --- Create endpoint ---

    def test_create_custom_config(self):
        """POST creates a new custom config with server-generated name."""
        create_data = {
            "data": {
                "type": "configs",
                "attributes": {
                    "display_date": False,
                    "display_clock": True,
                    "image_refresh_interval": 60000,
                },
            }
        }

        response = self.client.post(
            "/api/v1/configs", create_data, content_type="application/vnd.api+json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertTrue(data["data"]["attributes"]["name"].startswith("custom-"))
        self.assertFalse(data["data"]["attributes"]["display_date"])
        self.assertTrue(data["data"]["attributes"]["display_clock"])
        self.assertEqual(data["data"]["attributes"]["image_refresh_interval"], 60000)

    def test_create_without_is_active_defaults_to_inactive(self):
        """POST without is_active creates inactive config."""
        create_data = {
            "data": {
                "type": "configs",
                "attributes": {
                    "display_date": True,
                },
            }
        }

        response = self.client.post(
            "/api/v1/configs", create_data, content_type="application/vnd.api+json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertFalse(data["data"]["attributes"]["is_active"])

        # Original config should still be active
        self.config.refresh_from_db()
        self.assertTrue(self.config.is_active)

    def test_create_with_is_active_activates_new_config(self):
        """POST with is_active=true creates and activates new config."""
        create_data = {
            "data": {
                "type": "configs",
                "attributes": {
                    "display_date": False,
                    "is_active": True,
                },
            }
        }

        response = self.client.post(
            "/api/v1/configs", create_data, content_type="application/vnd.api+json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertTrue(data["data"]["attributes"]["name"].startswith("custom-"))
        self.assertTrue(data["data"]["attributes"]["is_active"])

        # Old active config should be deactivated
        self.config.refresh_from_db()
        self.assertFalse(self.config.is_active)

    def test_create_ignores_client_provided_name(self):
        """POST ignores client-provided name and generates server-side."""
        create_data = {
            "data": {
                "type": "configs",
                "attributes": {
                    "name": "my-custom-name",
                    "display_date": True,
                },
            }
        }

        response = self.client.post(
            "/api/v1/configs", create_data, content_type="application/vnd.api+json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        # Name should be server-generated, not client-provided
        self.assertTrue(data["data"]["attributes"]["name"].startswith("custom-"))
        self.assertNotEqual(data["data"]["attributes"]["name"], "my-custom-name")

    def test_create_returns_400_when_limit_exceeded(self):
        """POST returns 400 when config limit is reached."""
        from smplfrm.services.config_service import CONFIG_LIMIT

        for i in range(CONFIG_LIMIT - 1):
            Config.objects.create(name=f"config-{i}", is_active=False)

        create_data = {
            "data": {
                "type": "configs",
                "attributes": {"display_date": True},
            }
        }

        response = self.client.post(
            "/api/v1/configs", create_data, content_type="application/vnd.api+json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Activate via PUT ---

    def test_activate_via_put_with_is_active_true(self):
        """PUT with is_active=true activates target config."""
        other = Config.objects.create(name="custom-20260101", is_active=False)
        update_data = self._build_update_payload(other, is_active=True)

        response = self.client.put(
            f"/api/v1/configs/{other.external_id}",
            update_data,
            content_type="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["data"]["attributes"]["is_active"])
        self.assertEqual(data["data"]["id"], other.external_id)

        self.config.refresh_from_db()
        self.assertFalse(self.config.is_active)

    def test_activate_nonexistent_returns_403(self):
        """PUT on nonexistent config returns 403."""
        update_data = {
            "data": {
                "type": "configs",
                "id": "nonexistent12345",
                "attributes": {
                    "name": "test",
                    "is_active": True,
                },
            }
        }

        response = self.client.put(
            "/api/v1/configs/nonexistent12345",
            update_data,
            content_type="application/vnd.api+json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
