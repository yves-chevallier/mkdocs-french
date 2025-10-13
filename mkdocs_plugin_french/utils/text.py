from __future__ import annotations

import unicodedata


def strip_accents(value: str) -> str:
    """Retire les diacritiques d'une chaîne (utile pour les comparaisons)."""
    normalized = unicodedata.normalize("NFD", value)
    filtered = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", filtered)
