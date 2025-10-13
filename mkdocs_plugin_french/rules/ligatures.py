from __future__ import annotations

import re
from .base import RuleDefinition, RuleResult
from ..dictionary import dictionary

WORD_PATTERN = re.compile(r"\b[^\W\d_]+\b", re.UNICODE)


def _needs_ligature(word: str) -> bool:
    lowered = word.lower()
    return "oe" in lowered or "ae" in lowered


def det_ligatures(text: str) -> list[RuleResult]:
    results: list[RuleResult] = []
    for match in WORD_PATTERN.finditer(text):
        word = match.group(0)
        if not _needs_ligature(word):
            continue
        ligatured = dictionary.ligaturize(word)
        if ligatured == word:
            continue
        results.append(
            (
                match.start(),
                match.end(),
                f"Ligature : «{word}» → «{ligatured}»",
                ligatured,
            )
        )
    return results


def fix_ligatures(text: str) -> str:
    def repl(match: re.Match) -> str:
        word = match.group(0)
        if not _needs_ligature(word):
            return word
        return dictionary.ligaturize(word)

    return WORD_PATTERN.sub(repl, text)


RULE = RuleDefinition(
    name="ligatures",
    config_attr="ligatures",
    detector=det_ligatures,
    fixer=fix_ligatures,
)
