"""Canonical form for embedded photo tags.

The same keyword arrives from EXIF, IPTC, and XMP with different casing,
Unicode composition, padding, and stray control bytes. Every tag is reduced to
one canonical string before it is stored or compared, so "Family", "FAMILY",
and "family\\x00" are the same tag.

Pipeline (order matters):
1. Remove C0 control characters (U+0000-U+001F) and DEL (U+007F).
2. Unicode NFC, so decomposed and precomposed accents compare equal.
   https://unicode.org/reports/tr15/
3. Unicode casefold, which is stricter than lower() (for example "ß" -> "ss").
   https://docs.python.org/3/library/stdtypes.html#str.casefold
4. Collapse each run of whitespace to one space.
5. Strip leading and trailing whitespace.
"""

import re
import unicodedata
from typing import Optional

# Matches Tag.value / Tag.display_value max_length. Keywords longer than this
# are almost certainly captions or junk written into a keyword field.
MAX_TAG_LENGTH = 200

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_WHITESPACE_RUN = re.compile(r"\s+")


def _clean(value: str) -> str:
    value = _CONTROL_CHARS.sub("", value)
    value = unicodedata.normalize("NFC", value)
    return value


def _collapse(value: str) -> str:
    return _WHITESPACE_RUN.sub(" ", value).strip()


def canonicalize(value: object) -> Optional[str]:
    """Return the canonical form of a tag, or None if it is unusable.

    Args:
        value: Raw tag text from an image metadata source

    Returns:
        Canonical tag string, or None when the input is not a string, is empty
        after cleaning, or is longer than MAX_TAG_LENGTH.
    """
    if not isinstance(value, str):
        return None
    result = _collapse(_clean(value).casefold())
    if not result or len(result) > MAX_TAG_LENGTH:
        return None
    return result


def normalize_display(value: str) -> str:
    """Return the human-facing form of a tag: cleaned, case preserved.

    Args:
        value: Raw tag text from an image metadata source

    Returns:
        The cleaned tag text, truncated to MAX_TAG_LENGTH.
    """
    return _collapse(_clean(value))[:MAX_TAG_LENGTH]
