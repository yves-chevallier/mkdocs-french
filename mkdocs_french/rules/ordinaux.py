from __future__ import annotations

import re
from typing import Optional

from .base import RuleDefinition, RuleResult


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


def det_ordinaux(text: str) -> list[RuleResult]:
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


def fix_ordinaux(text: str) -> str:
    def repl(match: re.Match) -> str:
        number = match.group(1)
        suffix = match.group(2)
        normalized = _normalize_suffix(number, suffix)
        if not normalized:
            return match.group(0)
        return f"{number}^{normalized}^"

    return ORDINAL_PATTERN.sub(repl, text)


RULE = RuleDefinition(
    name="ordinaux", config_attr="ordinaux", detector=det_ordinaux, fixer=fix_ordinaux
)
