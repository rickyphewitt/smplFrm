from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from smplfrm.models import LibraryFilter
from smplfrm.tests.library_filter_fixtures import (
    activate_filter,
    make_image,
    set_filtering,
)


class TestImagesVisibility(TestCase):
    """With filtering on, images outside the active filter are not served."""

    def setUp(self):
        self.client = APIClient()
        self.shown = make_image("shown.jpg", tags=["frame"], with_meta=True)
        self.hidden = make_image("hidden.jpg", tags=["beach"], with_meta=True)
        set_filtering(True)
        activate_filter("frame")

    def ids(self, uri, params=None):
        response = self.client.get(uri, params or {})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        return [d["id"] for d in response.json()["data"]]

    def test_images_list_shows_only_matching_images(self):
        self.assertEqual(self.ids("/api/v1/images"), [self.shown.external_id])
        self.assertEqual(
            self.ids("/api/v1/images", {"sort": "display_priority"}),
            [self.shown.external_id],
        )

    def test_images_list_pagination_counts_only_matching_images(self):
        body = self.client.get("/api/v1/images").json()

        self.assertEqual(body["meta"]["pagination"]["count"], 1)

    def test_image_detail(self):
        self.assertEqual(
            self.client.get(f"/api/v1/images/{self.shown.external_id}").status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get(f"/api/v1/images/{self.hidden.external_id}").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_hidden_detail_looks_like_an_unknown_id(self):
        hidden = self.client.get(f"/api/v1/images/{self.hidden.external_id}")
        unknown = self.client.get("/api/v1/images/unknownImage0001")

        self.assertEqual(hidden.status_code, unknown.status_code)
        self.assertEqual(hidden.json(), unknown.json())

    def test_hidden_image_display_returns_403(self):
        hidden = self.client.get(f"/api/v1/images/{self.hidden.external_id}/display")
        unknown = self.client.get("/api/v1/images/unknownImage0001/display")

        self.assertEqual(hidden.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(hidden.content, unknown.content)

    def test_metadata_list_shows_only_matching_images(self):
        self.assertEqual(
            self.ids("/api/v1/images_metadata"), [self.shown.meta.external_id]
        )

    def test_metadata_filter_by_hidden_image_is_empty(self):
        self.assertEqual(
            self.ids(
                "/api/v1/images_metadata", {"filter[image]": self.hidden.external_id}
            ),
            [],
        )

    def test_metadata_detail(self):
        self.assertEqual(
            self.client.get(
                f"/api/v1/images_metadata/{self.shown.meta.external_id}"
            ).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get(
                f"/api/v1/images_metadata/{self.hidden.meta.external_id}"
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_filtering_on_without_active_filter_serves_nothing(self):
        LibraryFilter.objects.update(is_active=False)

        self.assertEqual(self.ids("/api/v1/images"), [])
        self.assertEqual(self.ids("/api/v1/images_metadata"), [])
        self.assertEqual(
            self.client.get(f"/api/v1/images/{self.shown.external_id}").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_filtering_off_serves_every_image(self):
        set_filtering(False)

        self.assertEqual(
            set(self.ids("/api/v1/images")),
            {self.shown.external_id, self.hidden.external_id},
        )
        self.assertEqual(
            self.client.get(f"/api/v1/images/{self.hidden.external_id}").status_code,
            status.HTTP_200_OK,
        )
