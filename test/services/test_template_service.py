import unittest
from services.template_service import TemplateService
from services.image_service import ImageService
from pathlib import Path

class TestTemplateService(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.service = TemplateService()

    def test_load_templates(self):
        templates = self.service.get_templates()
        self.assertEqual(len(templates), 1, "Unexpected number of templates loaded")
        self.assertIsNotNone(templates["image.html"])


    def test_render(self):
        image_tpl = self.service.get_templates()["image.html"]
        image = "what/a/greate/image.jpg"
        refresh_int = 30
        rendered_template = self.service.render("image.html", image=image)
        self.assertTrue(image in rendered_template, f"Failed to find image {image} in rendered template")
        self.assertTrue(image in rendered_template, f"Failed to find refresh interval {refresh_int} in rendered template")
        self.assertTrue("{{" not in rendered_template)
        self.assertTrue("}}" not in rendered_template)
