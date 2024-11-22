import unittest

from services.history_service import HistoryService
from services.template_service import TemplateService
from services.image_service import ImageService
from pathlib import Path

class TestHistoryService(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.service = HistoryService()

    def test_add_duplicate(self):
        """
        Test asserts that a file that already exists
        in the history file is rejected with an exception
        :return:
        """

        # add a file to the history
        self.service.add("foo") # succeeds
        with self.assertRaises(Exception):
            self.service.add("foo")
