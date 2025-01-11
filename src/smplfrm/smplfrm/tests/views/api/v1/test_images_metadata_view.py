import datetime

from django.test import TestCase, RequestFactory

from smplfrm.services import ImageMetadataService, ImageService
from smplfrm.services import LibraryService
from smplfrm.views.api.v1.images import Images as imageView
from django.db.models import ObjectDoesNotExist


class TestImagesMetadata(TestCase):
    def setUp(self):
        self.uri = "/api/v1/images_metadata"
        self.image_metadata_service = ImageMetadataService()
        self.image_service = ImageService()
        self.full_image_data = {
            "name": "foo",
            "file_path": "./nested/file/",
            "file_name": "image.jpg"
        }

    def test_list_read_update_delete(self):

        # get a list of 0 before adding any images
        response = self.client.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0, "Shouldn't find any image metadata at this time")

        # create images
        created_image = self.image_service.create(self.full_image_data)
        created_image2 = self.image_service.create(
            {
                "name": "second_image",
                "file_path": "foo",
                "file_name": "foo.jpg"
             }
        )
        # create meta for images
        image_meta = {
            "image": created_image,
            "exif": {"foo": "bar"},
            "taken": datetime.datetime.now()
        }


        created_image_meta = self.image_metadata_service.create(image_meta)

        response = self.client.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1, "Should find a single metadata record")


        # get single image meta by external id
        response = self.client.get(f"{self.uri}/{created_image_meta.external_id}")
        self.assertEqual(response.status_code, 200)
        single_response = response.json()
        self.assertEqual(single_response["id"], created_image_meta.external_id)
        self.assertEqual(single_response["taken"], created_image_meta.taken)
        self.assertIsNotNone(single_response["created"])
        self.assertIsNotNone(single_response["updated"])


        image_meta2 = {
            "image": created_image2,
            "exif": {"foo": "bar"},
            "taken": datetime.datetime.now()
        }
        created_image2_meta = self.image_metadata_service.create(image_meta2)

        # get the same metadata by image ext id
        response = self.client.get(f"{self.uri}?image__external_id={created_image.external_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1, "Should find a single metadata record")



        # assert no create/update/delete from UI for now
        response = self.client.post(f"{self.uri}")
        self.assertEqual(response.status_code, 403)
        response = self.client.put(f"{self.uri}/{created_image.external_id}")
        self.assertEqual(response.status_code, 403)
        response = self.client.delete(f"{self.uri}/{created_image.external_id}")
        self.assertEqual(response.status_code, 403)