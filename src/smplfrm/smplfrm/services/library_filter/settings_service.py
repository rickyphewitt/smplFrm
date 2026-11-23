from typing import Any, Dict

from django.db.models import QuerySet

from smplfrm.models import LibraryFilterSettings
from smplfrm.services.base_service import BaseService


class LibraryFilterSettingsService(BaseService):
    """Service for the single library filter settings row.

    The row is created by a data migration. It cannot be created or deleted
    through this service; get() recreates it, disabled, if it is ever missing.
    """

    def get(self) -> LibraryFilterSettings:
        """Return the settings row.

        Returns:
            The LibraryFilterSettings singleton
        """
        settings = (
            LibraryFilterSettings.objects.filter(deleted=False).order_by("id").first()
        )
        if settings is None:
            settings = LibraryFilterSettings.objects.create(enabled=False)
        return settings

    def set_enabled(
        self, settings: LibraryFilterSettings, enabled: bool
    ) -> LibraryFilterSettings:
        """Turn library filtering on or off.

        Args:
            settings: The settings row
            enabled: New value

        Returns:
            The updated settings row
        """
        settings.enabled = enabled
        return self.update(settings)

    def create(self, data: Dict[str, Any]) -> LibraryFilterSettings:
        raise NotImplementedError("Library filter settings is a single migrated row")

    def read(self, ext_id: str, deleted: bool = False) -> LibraryFilterSettings:
        """Retrieve the settings row by external ID.

        Args:
            ext_id: External identifier
            deleted: Whether to include soft-deleted records

        Returns:
            LibraryFilterSettings instance
        """
        return LibraryFilterSettings.objects.get(external_id=ext_id, deleted=deleted)

    def list(self, **kwargs) -> QuerySet[LibraryFilterSettings]:
        """List settings rows (one in practice).

        Args:
            **kwargs: Filter parameters

        Returns:
            QuerySet of non-deleted LibraryFilterSettings, ordered by id
        """
        return LibraryFilterSettings.objects.filter(deleted=False, **kwargs).order_by(
            "id"
        )

    def update(self, entity: LibraryFilterSettings) -> LibraryFilterSettings:
        """Persist the settings row.

        Args:
            entity: Settings row to save

        Returns:
            The saved settings row
        """
        entity.save()
        return entity

    def delete(self, ext_id: str) -> None:
        raise NotImplementedError("Library filter settings cannot be deleted")

    def destroy(self, ext_id: str) -> None:
        raise NotImplementedError("Library filter settings cannot be deleted")
