"""Text helpers used within mkdocs-french."""

from __future__ import annotations

import unicodedata


def strip_accents(value: str) -> str:
    """Remove diacritics from a string for comparison purposes.

    Args:
        value: Input string whose diacritics should be stripped.

    Returns:
        The normalized string without combining marks.
    """
    normalized = unicodedata.normalize("NFD", value)
    filtered = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", filtered)
