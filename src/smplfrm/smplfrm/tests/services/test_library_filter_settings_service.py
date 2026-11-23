from django.test import TestCase

from smplfrm.models import LibraryFilterSettings
from smplfrm.services.library_filter.settings_service import (
    LibraryFilterSettingsService,
)


class TestLibraryFilterSettingsService(TestCase):
    def setUp(self):
        self.service = LibraryFilterSettingsService()

    def test_get_returns_the_seeded_row(self):
        settings = self.service.get()

        self.assertEqual(settings, LibraryFilterSettings.objects.get())
        self.assertFalse(settings.enabled)

    def test_get_recreates_a_missing_row_disabled(self):
        LibraryFilterSettings.objects.all().delete()

        settings = self.service.get()

        self.assertFalse(settings.enabled)
        self.assertEqual(LibraryFilterSettings.objects.count(), 1)

    def test_set_enabled_persists(self):
        settings = self.service.get()

        self.service.set_enabled(settings, True)

        self.assertTrue(LibraryFilterSettings.objects.get().enabled)

    def test_read_and_list(self):
        settings = self.service.get()

        self.assertEqual(self.service.read(settings.external_id), settings)
        self.assertEqual(list(self.service.list()), [settings])

    def test_update_saves_the_row(self):
        settings = self.service.get()
        settings.enabled = True

        self.service.update(settings)

        self.assertTrue(LibraryFilterSettings.objects.get().enabled)

    def test_singleton_cannot_be_created_or_deleted(self):
        settings = self.service.get()
        with self.assertRaises(NotImplementedError):
            self.service.create({"enabled": True})
        with self.assertRaises(NotImplementedError):
            self.service.delete(settings.external_id)
        with self.assertRaises(NotImplementedError):
            self.service.destroy(settings.external_id)
