"""Read embedded keyword tags from an image file.

Sources, in read order (the first source to supply a tag sets its display
form):

- EXIF ``XPKeywords`` (0x9C9E): UTF-16LE bytes, NUL-terminated, split on ';'.
- IPTC ``Keywords`` (record 2, dataset 25): bytes or a list of bytes; UTF-8
  with a Latin-1 fallback for older tools.
- XMP ``dc:subject`` and ``lr:hierarchicalSubject``. Pillow exposes the raw
  XMP packet in ``Image.info["xmp"]``; it is parsed here with the standard
  library. ``Image.getxmp()`` is not used because it needs the optional
  ``defusedxml`` package and silently returns ``{}`` without it.
  https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.getxmp

XMP is untrusted XML from the photo file. Packets over MAX_XMP_BYTES or with a
DOCTYPE/ENTITY declaration are skipped before parsing. The bundled expat
(>= 2.4.1) also blocks entity-expansion attacks and ElementTree never fetches
external entities; the pre-check is defense in depth.
https://docs.python.org/3/library/xml.html#xml-vulnerabilities

A failure in one source is logged at DEBUG and does not stop the others.
Tag text may contain personal names, so it is never logged above DEBUG.
"""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional, Tuple

from PIL import Image as PIL_Image
from PIL import IptcImagePlugin

from smplfrm.services.library.canonicalize import canonicalize, normalize_display

logger = logging.getLogger(__name__)

SOURCE_EXIF = "exif"
SOURCE_IPTC = "iptc"
SOURCE_XMP = "xmp"

EXIF_XP_KEYWORDS = 0x9C9E
IPTC_KEYWORDS = (2, 25)

# Real-world XMP packets are a few KB; JPEG caps a single APP1 segment at
# 64 KB. 1 MiB leaves room for large PNG/WebP packets while bounding parse
# cost for hostile files.
MAX_XMP_BYTES = 1024 * 1024

HIERARCHY_DELIMITER = "|"

_RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
_DC_SUBJECT = "{http://purl.org/dc/elements/1.1/}subject"
_LR_HIERARCHICAL_SUBJECT = "{http://ns.adobe.com/lightroom/1.0/}hierarchicalSubject"

# (tag text, full hierarchical path or None)
_RawTag = Tuple[str, Optional[str]]


@dataclass(frozen=True)
class ExtractedTag:
    """One canonical tag found in an image, with where it came from."""

    canonical: str
    display: str
    sources: Tuple[str, ...]
    raw_hierarchy: Tuple[str, ...]


@dataclass
class _Pending:
    canonical: str
    display: str
    sources: set = field(default_factory=set)
    raw_hierarchy: List[str] = field(default_factory=list)

    def finalize(self) -> ExtractedTag:
        return ExtractedTag(
            canonical=self.canonical,
            display=self.display,
            sources=tuple(sorted(self.sources)),
            raw_hierarchy=tuple(self.raw_hierarchy),
        )


class TagExtractor:
    """Extract canonical tags from EXIF, IPTC, and XMP metadata."""

    def extract(self, image_path: str) -> List[ExtractedTag]:
        """Return the deduplicated tags embedded in an image.

        Args:
            image_path: Path to the image file

        Returns:
            Tags in first-seen order. Empty when the file cannot be opened or
            carries no usable keywords. Never raises for unreadable metadata.
        """
        readers: Tuple[Tuple[str, Callable[[PIL_Image.Image], List[_RawTag]]], ...] = (
            (SOURCE_EXIF, self._read_exif),
            (SOURCE_IPTC, self._read_iptc),
            (SOURCE_XMP, self._read_xmp),
        )
        pending: dict[str, _Pending] = {}

        try:
            with PIL_Image.open(image_path) as img:
                for source, reader in readers:
                    try:
                        raw_tags = reader(img)
                    except Exception:
                        logger.debug(
                            "Skipping unreadable %s tags in %s",
                            source,
                            image_path,
                            exc_info=True,
                        )
                        continue
                    self._merge(pending, source, raw_tags)
        except Exception:
            logger.debug(
                "Unable to open %s for tag extraction", image_path, exc_info=True
            )
            return []

        return [p.finalize() for p in pending.values()]

    @staticmethod
    def _merge(
        pending: dict[str, _Pending], source: str, raw_tags: Iterable[_RawTag]
    ) -> None:
        for value, hierarchy in raw_tags:
            canonical = canonicalize(value)
            if canonical is None:
                continue
            entry = pending.get(canonical)
            if entry is None:
                entry = _Pending(canonical=canonical, display=normalize_display(value))
                pending[canonical] = entry
            entry.sources.add(source)
            if hierarchy and hierarchy not in entry.raw_hierarchy:
                entry.raw_hierarchy.append(hierarchy)

    @staticmethod
    def _read_exif(img: PIL_Image.Image) -> List[_RawTag]:
        value = img.getexif().get(EXIF_XP_KEYWORDS)
        if value is None:
            return []
        if isinstance(value, (tuple, list)):
            value = bytes(value)
        if isinstance(value, bytes):
            value = value.decode("utf-16-le", errors="replace")
        if not isinstance(value, str):
            return []
        return [(part, None) for part in value.replace("\x00", "").split(";")]

    @staticmethod
    def _read_iptc(img: PIL_Image.Image) -> List[_RawTag]:
        info = IptcImagePlugin.getiptcinfo(img)
        if not info:
            return []
        value = info.get(IPTC_KEYWORDS)
        if value is None:
            return []
        values = value if isinstance(value, list) else [value]
        result = []
        for raw in values:
            if not isinstance(raw, bytes):
                continue
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("latin-1")
            result.append((text, None))
        return result

    @staticmethod
    def _read_xmp(img: PIL_Image.Image) -> List[_RawTag]:
        packet = img.info.get("xmp")
        if not packet:
            return []
        if isinstance(packet, bytes):
            if len(packet) > MAX_XMP_BYTES:
                raise ValueError("XMP packet exceeds size limit")
            packet = packet.decode("utf-8")
        if not isinstance(packet, str):
            return []
        if len(packet.encode("utf-8")) > MAX_XMP_BYTES:
            raise ValueError("XMP packet exceeds size limit")
        if "<!DOCTYPE" in packet or "<!ENTITY" in packet:
            raise ValueError("XMP packet declares a DTD")

        root = ET.fromstring(packet.lstrip("\ufeff"))
        result: List[_RawTag] = []
        for subject in root.iter(_DC_SUBJECT):
            for item in subject.iter(f"{_RDF}li"):
                if item.text:
                    result.append((item.text, None))
        for subject in root.iter(_LR_HIERARCHICAL_SUBJECT):
            for item in subject.iter(f"{_RDF}li"):
                if item.text:
                    path = item.text.strip()
                    leaf = path.split(HIERARCHY_DELIMITER)[-1]
                    result.append((leaf, path))
        return result
