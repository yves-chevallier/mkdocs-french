"""Rule that enforces Markdown-style ordinal notation (``1^er^``)."""

from __future__ import annotations

import re
from typing import Optional

from .base import Rule, RuleResult


ORDINAL_SUFFIXES = [
    "ières",
    "ière",
    "ieres",
    "iere",
    "èmes",
    "ème",
    "iemes",
    "ieme",
    "ièmes",
    "ième",
    "eres",
    "ere",
    "ères",
    "ère",
    "ers",
    "er",
    "ires",
    "ire",
    "res",
    "re",
    "emes",
    "eme",
    "es",
    "e",
]

ORDINAL_PATTERN = re.compile(
    rf"\b(\d+)\s*(?<!\^)({'|'.join(ORDINAL_SUFFIXES)})\b", re.IGNORECASE
)

REPLACEMENTS = {
    "ières": "ires",
    "ière": "ire",
    "ieres": "ires",
    "iere": "ire",
    "ièmes": "iemes",
    "ième": "ieme",
    "èmes": "emes",
    "ème": "eme",
    "ires": "res",
    "ire": "re",
    "ères": "res",
    "ère": "re",
}

FIRST_SUFFIX_MAP = {
    "er": "er",
    "ier": "er",
    "ers": "ers",
    "iers": "ers",
    "re": "re",
    "ire": "re",
    "res": "res",
    "ires": "res",
    "ere": "re",
    "eres": "res",
    "eme": "er",
    "emes": "ers",
    "e": "er",
    "es": "ers",
}

GENERAL_SUFFIX_MAP = {
    "eme": "e",
    "emes": "es",
    "e": "e",
    "es": "es",
    "ieme": "e",
    "iemes": "es",
}


def _normalize_suffix(number: str, suffix: str) -> Optional[str]:
    """Return the normalized suffix for a given ordinal number.

    Args:
        number: Numeric portion captured from the input text.
        suffix: Raw suffix captured from the input text.

    Returns:
        The normalized suffix to use inside the caret markers, or ``None`` when
        the suffix should stay untouched.

    Examples:
        >>> from mkdocs_french.rules.ordinaux import _normalize_suffix
        >>> _normalize_suffix("1", "ère")
        're'
        >>> _normalize_suffix("2", "ieme")
        'e'
        >>> _normalize_suffix("3", "er") is None
        True
    """
    normalized = suffix.lower()
    for original, replacement in sorted(
        REPLACEMENTS.items(), key=lambda item: -len(item[0])
    ):
        normalized = normalized.replace(original, replacement)

    if number == "1":
        return FIRST_SUFFIX_MAP.get(normalized)

    if normalized in {"er", "ers", "re", "res", "ier", "iers", "ire", "ires"}:
        return None

    return GENERAL_SUFFIX_MAP.get(normalized)


class OrdinauxRule(Rule):
    """Convert textual ordinal suffixes into Markdown caret notation."""

    def __init__(self) -> None:
        """Register the rule in the orchestrator."""
        super().__init__(name="ordinaux", config_attr="ordinaux")

    def detect(self, text: str) -> list[RuleResult]:
        """Return warnings for ordinals written without caret markers.

        Args:
            text: Text fragment to inspect.

        Returns:
            A list of rule results containing the normalized replacement in the
            preview field.
        """
        results: list[RuleResult] = []
        for match in ORDINAL_PATTERN.finditer(text):
            number = match.group(1)
            suffix = match.group(2)
            normalized = _normalize_suffix(number, suffix)
            if not normalized:
                continue
            replacement = f"{number}^{normalized}^"
            results.append(
                (
                    match.start(),
                    match.end(),
                    f"Ordinal «{match.group(0)}» → «{replacement}»",
                    replacement,
                )
            )
        return results

    def fix(self, text: str) -> str:
        """Apply caret-based notation (``1^er^``) directly in the text.

        Args:
            text: Text fragment to mutate.

        Returns:
            The updated text where detected ordinals use normalized suffixes.
        """
        def repl(match: re.Match) -> str:
            number = match.group(1)
            suffix = match.group(2)
            normalized = _normalize_suffix(number, suffix)
            if not normalized:
                return match.group(0)
            return f"{number}^{normalized}^"

        return ORDINAL_PATTERN.sub(repl, text)
