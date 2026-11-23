"""Helpers that set up library filtering state for tests."""

from typing import Iterable

from smplfrm.models import (
    Image,
    ImageMetadata,
    ImageTag,
    LibraryFilter,
    LibraryFilterRule,
    LibraryFilterSettings,
    Tag,
)


def get_tag(value: str) -> Tag:
    tag, _ = Tag.objects.get_or_create(value=value, defaults={"display_value": value})
    return tag


def make_image(
    name: str, tags: Iterable[str] = (), deleted: bool = False, with_meta: bool = False
) -> Image:
    """Create an image row linked to the given tag values."""
    image = Image.objects.create(
        name=name, file_name=name, file_path=f"/library/{name}", deleted=deleted
    )
    for value in tags:
        ImageTag.objects.create(image=image, tag=get_tag(value))
    if with_meta:
        ImageMetadata.objects.create(image=image, exif={})
    return image


def set_filtering(enabled: bool) -> LibraryFilterSettings:
    settings = LibraryFilterSettings.objects.get()
    settings.enabled = enabled
    settings.save()
    return settings


def activate_filter(*tag_values: str, name: str = "frame") -> LibraryFilter:
    """Create the active filter with one tag rule per value."""
    library_filter = LibraryFilter.objects.create(name=name, is_active=True)
    for value in tag_values:
        LibraryFilterRule.objects.create(
            library_filter=library_filter, tag=get_tag(value)
        )
    return library_filter
