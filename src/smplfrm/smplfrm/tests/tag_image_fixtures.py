"""Build small test images that carry embedded keyword metadata.

Images are generated at test time so the repository does not hold binary
fixtures for every metadata combination. Each helper writes one source the
way common photo tools do:

- EXIF XPKeywords (0x9C9E): UTF-16LE, NUL-terminated, ';'-separated
  (Windows Explorer).
- IPTC Keywords (record 2, dataset 25) inside a Photoshop APP13 segment
  (Lightroom, digiKam). Pillow can read IPTC but cannot write it, so the
  segment is assembled by hand.
- XMP dc:subject and lr:hierarchicalSubject (Lightroom, Apple Photos).
"""

import struct
from typing import Iterable, Optional
from xml.sax.saxutils import escape

from PIL import Image, PngImagePlugin

XP_KEYWORDS_TAG = 0x9C9E


def xp_keywords_bytes(keywords: Iterable[str]) -> bytes:
    return ";".join(keywords).encode("utf-16-le") + b"\x00\x00"


def xmp_packet(
    subjects: Iterable[str] = (),
    hierarchical: Iterable[str] = (),
    subject_container: str = "Bag",
) -> str:
    subject_items = "".join(f"<rdf:li>{escape(s)}</rdf:li>" for s in subjects)
    hierarchy_items = "".join(f"<rdf:li>{escape(h)}</rdf:li>" for h in hierarchical)
    return (
        '<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about=""'
        ' xmlns:dc="http://purl.org/dc/elements/1.1/"'
        ' xmlns:lr="http://ns.adobe.com/lightroom/1.0/">'
        f"<dc:subject><rdf:{subject_container}>{subject_items}"
        f"</rdf:{subject_container}></dc:subject>"
        f"<lr:hierarchicalSubject><rdf:Bag>{hierarchy_items}</rdf:Bag>"
        "</lr:hierarchicalSubject>"
        "</rdf:Description></rdf:RDF></x:xmpmeta>"
        '<?xpacket end="w"?>'
    )


def _iptc_app13_segment(keywords: Iterable[bytes]) -> bytes:
    iptc = b"".join(b"\x1c\x02\x19" + struct.pack(">H", len(k)) + k for k in keywords)
    if len(iptc) % 2:
        iptc += b"\x00"
    resource = (
        b"8BIM"
        + struct.pack(">H", 0x0404)  # IPTC-NAA resource id
        + b"\x00\x00"  # empty, even-padded Pascal name
        + struct.pack(">I", len(iptc))
        + iptc
    )
    payload = b"Photoshop 3.0\x00" + resource
    return b"\xff\xed" + struct.pack(">H", len(payload) + 2) + payload


def write_tagged_image(
    path: str,
    image_format: str = "JPEG",
    xp_keywords: Optional[Iterable[str]] = None,
    iptc_keywords: Optional[Iterable[bytes]] = None,
    xmp: Optional[str] = None,
) -> str:
    """Write a 4x4 image with the requested metadata and return its path."""
    image = Image.new("RGB", (4, 4), color=(120, 80, 40))
    save_kwargs = {}

    if xp_keywords is not None:
        exif = Image.Exif()
        exif[XP_KEYWORDS_TAG] = xp_keywords_bytes(xp_keywords)
        save_kwargs["exif"] = exif.tobytes()

    if xmp is not None:
        if image_format == "PNG":
            info = PngImagePlugin.PngInfo()
            info.add_itxt("XML:com.adobe.xmp", xmp)
            save_kwargs["pnginfo"] = info
        else:
            save_kwargs["xmp"] = xmp.encode("utf-8")

    image.save(path, image_format, **save_kwargs)

    if iptc_keywords is not None:
        if image_format != "JPEG":
            raise ValueError("IPTC fixtures are only supported for JPEG")
        with open(path, "rb") as fh:
            data = fh.read()
        # Insert APP13 directly after the SOI marker.
        data = data[:2] + _iptc_app13_segment(iptc_keywords) + data[2:]
        with open(path, "wb") as fh:
            fh.write(data)

    return path
