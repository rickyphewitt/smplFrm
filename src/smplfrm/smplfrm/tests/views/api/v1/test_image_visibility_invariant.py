"""Every image-serving route must hide images outside the active filter.

Routes are discovered from the URL resolver, so a new route under
api/v1/images or api/v1/images_metadata fails this test until it has a
visibility check below or is listed in UNGATED_ROUTES with a reason.
"""

import re

from django.test import TestCase
from django.urls import URLResolver, get_resolver, reverse
from rest_framework import status
from rest_framework.test import APIClient

from smplfrm.tests.library_filter_fixtures import (
    activate_filter,
    make_image,
    set_filtering,
)

IMAGE_ROUTE = re.compile(r"^api/v1/images(_metadata)?(/|$|\\\.)")

# Route name -> reason the route does not need the visibility gate.
UNGATED_ROUTES: dict[str, str] = {}


def image_route_names():
    """Return the names of every registered route under the image prefixes."""

    def walk(patterns, prefix=""):
        for pattern in patterns:
            if isinstance(pattern, URLResolver):
                yield from walk(pattern.url_patterns, prefix + str(pattern.pattern))
            else:
                yield prefix + str(pattern.pattern), pattern.name

    names = set()
    for path, name in walk(get_resolver().url_patterns):
        if IMAGE_ROUTE.match(path.replace("^", "").replace("$", "")):
            names.add(name)
    return names


class TestImageVisibilityInvariant(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.shown = make_image("shown.jpg", tags=["frame"], with_meta=True)
        self.hidden = make_image("hidden.jpg", tags=["beach"], with_meta=True)
        set_filtering(True)
        activate_filter("frame")

        self.checks = {
            "images-list": self.check_images_list,
            "images-detail": self.check_images_detail,
            "images-display-image": self.check_images_display,
            "images_metadata-list": self.check_metadata_list,
            "images_metadata-detail": self.check_metadata_detail,
        }

    def list_ids(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return {d["id"] for d in response.json()["data"]}

    def check_images_list(self):
        ids = self.list_ids(reverse("images-list"))
        self.assertIn(self.shown.external_id, ids)
        self.assertNotIn(self.hidden.external_id, ids)

    def check_images_detail(self):
        url = reverse("images-detail", kwargs={"external_id": self.hidden.external_id})
        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)

    def check_images_display(self):
        url = reverse(
            "images-display-image", kwargs={"external_id": self.hidden.external_id}
        )
        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)

    def check_metadata_list(self):
        ids = self.list_ids(reverse("images_metadata-list"))
        self.assertIn(self.shown.meta.external_id, ids)
        self.assertNotIn(self.hidden.meta.external_id, ids)

    def check_metadata_detail(self):
        url = reverse(
            "images_metadata-detail",
            kwargs={"external_id": self.hidden.meta.external_id},
        )
        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)

    def test_discovery_finds_the_image_routes(self):
        self.assertTrue(
            {"images-list", "images_metadata-list"} <= image_route_names(),
            "Route discovery is broken; the invariant below would pass vacuously",
        )

    def test_every_image_route_is_checked_or_exempt(self):
        unchecked = image_route_names() - set(self.checks) - set(UNGATED_ROUTES)

        self.assertEqual(
            unchecked,
            set(),
            "New image route(s) without a visibility check. Route them through "
            "ImageService.visible_queryset() and add a check here, or list them "
            "in UNGATED_ROUTES with a reason.",
        )

    def test_every_checked_route_hides_filtered_out_images(self):
        for name in sorted(image_route_names() & set(self.checks)):
            with self.subTest(route=name):
                self.checks[name]()
