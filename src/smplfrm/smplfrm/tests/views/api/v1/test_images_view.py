from django.test import TestCase, RequestFactory

from smplfrm.services import ImageService, LibraryService
from smplfrm.views.api.v1.images import Images as imageView
from django.db.models import ObjectDoesNotExist


class TestImagesView(TestCase):
    def setUp(self):
        self.uri = "/api/v1/images"
        self.image_service = ImageService()
        self.full_image_data = {
            "name": "foo",
            "file_path": "./nested/file/",
            "file_name": "image.jpg",
        }

    def test_list_read_update_delete(self):

        # get a list of 0 before adding any images
        response = self.client.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.json()), 0, "Shouldn't find any images at this time"
        )

        # create an image
        created_image = self.image_service.create(self.full_image_data)

        response = self.client.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1, "Should find one image")

        # get single image by external id
        response = self.client.get(f"{self.uri}/{created_image.external_id}")
        self.assertEqual(response.status_code, 200)

        # assert no create/update/delete from UI for now
        response = self.client.post(f"{self.uri}")
        self.assertEqual(response.status_code, 403)
        response = self.client.put(f"{self.uri}/{created_image.external_id}")
        self.assertEqual(response.status_code, 403)
        response = self.client.delete(f"{self.uri}/{created_image.external_id}")
        self.assertEqual(response.status_code, 403)

    def test_display_image(self):
        # bootstrap the images so they can be read
        LibraryService().scan()

        # get a random image
        image = self.image_service.list()[0]

        response = self.client.get(f"{self.uri}/{image.external_id}/display")
        self.assertEqual(response.status_code, 200)

        # assert view count was updated
        displayed_image = self.image_service.read(image.external_id)
        self.assertEqual(image.view_count + 1, displayed_image.view_count)

    def test_display_cached_image(self):
        # bootstrap the images so they can be read
        LibraryService().scan()

        # get a random image
        image = self.image_service.list()[0]

        # this will cache image
        response = self.client.get(f"{self.uri}/{image.external_id}/display")
        self.assertEqual(response.status_code, 200)

        # update image to point to a file that doesn't exist
        image.file_path = "/does/Not/Exist.jpg"
        self.image_service.update(image)

        # still able to get it from the cache
        response = self.client.get(f"{self.uri}/{image.external_id}/display")
        self.assertEqual(response.status_code, 200)

        # assert view count was updated
        displayed_image = self.image_service.read(image.external_id)
        self.assertEqual(image.view_count + 1, displayed_image.view_count)

    def test_image_not_found(self):
        # bootstrap the images so they can be read
        LibraryService().scan()

        # get a random image
        image = self.image_service.list()[0]
        # update image to point to a file that doesn't exist
        image.file_path = "/does/Not/Exist.jpg"
        self.image_service.update(image)

        # attempt to display image that doesn't exist
        # @ToDo use a fake image instead of 404
        response = self.client.get(
            f"{self.uri}/{image.external_id}/display?width=1&height=2"
        )
        self.assertEqual(response.status_code, 404)

    def test_next_image(self):
        """
        Returns the next image
        :return:
        """

        # bootstrap the images so they can be read
        LibraryService().scan()

        response = self.client.get(f"{self.uri}/next")
        self.assertEqual(response.status_code, 200)

    def _assert_image(self, image, name="name"):
        self.assertIsNotNone(image.external_id, "External Id should be set on Create.")
        self.assertIsNotNone(image.external_id, "External Id should be set on Create.")
        self.assertIsNotNone(image.created, "Created Datetime not set.")
        self.assertIsNotNone(image.updated, "Updated Datetime not set.")
        self.assertEqual(image.name, self.full_image_data[name], "Name not set.")
        self.assertEqual(
            image.file_path, self.full_image_data["file_path"], "File_path not set."
        )
        self.assertEqual(
            image.file_name, self.full_image_data["file_name"], "File_name not set."
        )
