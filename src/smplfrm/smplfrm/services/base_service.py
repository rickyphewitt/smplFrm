import abc
from typing import Any, Dict, Optional


class BaseService(abc.ABC):
    """Abstract base class for service layer implementations.

    Provides CRUD operations interface for data access and business logic.
    """

    @abc.abstractmethod
    def create(self, data: Dict[str, Any]) -> Any:
        """Create a new entity with the provided data.

        Args:
            data: Dictionary containing entity attributes

        Returns:
            The created entity instance
        """
        pass

    @abc.abstractmethod
    def read(self, ext_id: str, deleted: bool = False) -> Any:
        """Retrieve an entity by its external ID.

        Args:
            ext_id: External identifier of the entity
            deleted: Whether to include soft-deleted entities

        Returns:
            The entity instance if found
        """
        pass

    @abc.abstractmethod
    def list(self, **kwargs) -> Any:
        """List entities with optional filtering.

        Args:
            **kwargs: Filter parameters

        Returns:
            Collection of entity instances
        """
        pass

    @abc.abstractmethod
    def update(self, entity: Any) -> Any:
        """Update an existing entity.

        Args:
            entity: The entity instance to update

        Returns:
            The updated entity instance
        """
        pass

    @abc.abstractmethod
    def delete(self, ext_id: str) -> None:
        """Soft delete an entity by its external ID.

        Args:
            ext_id: External identifier of the entity
        """
        pass

    @abc.abstractmethod
    def destroy(self, ext_id: str) -> None:
        """Permanently delete an entity by its external ID.

        Args:
            ext_id: External identifier of the entity
        """
        pass
