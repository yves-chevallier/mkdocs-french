from __future__ import annotations

import re
from typing import List

from .base import RuleDefinition, RuleResult
from ..dictionary import get_dictionary

WORD_PATTERN = re.compile(r"\b[^\W\d_]+\b", re.UNICODE)


def det_diacritics(text: str) -> List[RuleResult]:
    results: List[RuleResult] = []
    dictionary = get_dictionary()

    for match in WORD_PATTERN.finditer(text):
        word = match.group(0)
        if not word:
            continue
        if not word.isupper():
            continue
        accented = dictionary.accentize(word)
        if accented == word:
            continue
        results.append(
            (
                match.start(),
                match.end(),
                f"Diacritique manquant : «{word}» → «{accented}»",
                accented,
            )
        )
    return results


def fix_diacritics(text: str) -> str:
    dictionary = get_dictionary()

    def repl(match: re.Match) -> str:
        word = match.group(0)
        if not word.isupper():
            return word
        accented = dictionary.accentize(word)
        return accented or word

    return WORD_PATTERN.sub(repl, text)


RULE = RuleDefinition(
    name="diacritics",
    config_attr="diacritics",
    detector=det_diacritics,
    fixer=fix_diacritics,
)
