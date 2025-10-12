from __future__ import annotations

import re
from typing import List

from .base import RuleDefinition, RuleResult
from ..dictionary import dictionary
from ..utils.text import strip_accents

WORD_PATTERN = re.compile(r"\b[^\W\d_]+\b", re.UNICODE)


def _apply_case(accented: str, original: str) -> str:
    if original.isupper():
        return accented.upper()
    if original.islower():
        return accented.lower()
    if original[0].isupper() and original[1:].islower():
        return accented[0] + accented[1:].lower()
    return accented


def _lookup_with_wordfreq(word: str) -> str | None:
    if top_n_list is None:
        return None
    base = strip_accents(word).lower()
    try:
        forms = top_n_list(base, "fr", 10)
    except Exception:  # pragma: no cover - wordfreq peut lever des erreurs internes
        return None
    for form in forms:
        if strip_accents(form) == base and form.lower() != base:
            return form
    return None


def det_diacritics(text: str) -> List[RuleResult]:
    results: List[RuleResult] = []
    for match in WORD_PATTERN.finditer(text):
        word = match.group(0)
        if not word:
            continue
        if not (word.isupper() or (word[0].isupper() and word[1:].islower())):
            continue
        accented = dictionary.accentize(word)
        if not accented:
            continue
        replacement = _apply_case(accented, word)
        if replacement == word:
            continue
        results.append(
            (
                match.start(),
                match.end(),
                f"Diacritique manquant : «{word}» → «{replacement}»",
                replacement,
            )
        )
    return results


def fix_diacritics(text: str) -> str:
    def repl(match: re.Match) -> str:
        word = match.group(0)
        if not (word.isupper() or (word[0].isupper() and word[1:].islower())):
            return word
        accented = dictionary.accentize(word)
        if not accented:
            return word
        replacement = _apply_case(accented, word)
        return replacement or word

    return WORD_PATTERN.sub(repl, text)


RULE = RuleDefinition(
    name="diacritics",
    config_attr="diacritics",
    detector=det_diacritics,
    fixer=fix_diacritics,
)
