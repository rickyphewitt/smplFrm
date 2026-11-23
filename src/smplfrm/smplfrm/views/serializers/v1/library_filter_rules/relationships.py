from typing import Any, Dict, Optional


def relationship_id(data: Dict[str, Any], name: str) -> Optional[str]:
    """Return the id of a to-one relationship from a parsed JSON:API document.

    The JSON:API parser turns ``relationships.<name>.data`` into
    ``data[name] = {"type": ..., "id": ...}`` (or None for ``"data": null``).

    Args:
        data: request.data after JSON:API parsing
        name: Relationship name

    Returns:
        The related resource id, or None when the relationship is absent,
        null, or malformed.
    """
    value = data.get(name)
    if not isinstance(value, dict):
        return None
    resource_id = value.get("id")
    if not isinstance(resource_id, str) or not resource_id:
        return None
    return resource_id
