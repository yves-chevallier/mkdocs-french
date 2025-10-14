"""Rule that restores missing uppercase diacritics using Morphalou data."""

from __future__ import annotations

import re
from typing import List

from ..dictionary import get_dictionary
from .base import Rule, RuleResult


WORD_PATTERN = re.compile(r"\b[^\W\d_]+\b", re.UNICODE)


class DiacriticsRule(Rule):
    """Insert missing accents in uppercase French words."""

    def __init__(self) -> None:
        """Register the rule in the orchestrator."""
        super().__init__(name="diacritics", config_attr="diacritics")

    def detect(self, text: str) -> List[RuleResult]:
        """Return warnings for uppercase words missing diacritics.

        Args:
            text: Text fragment to inspect.

        Returns:
            A list of rule results previewing the accentized version of each word.
        """
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

    def fix(self, text: str) -> str:
        """Add diacritics to uppercase words directly in the provided text.

        Args:
            text: Text fragment to mutate.

        Returns:
            The updated text where uppercase French words now include the proper
            accents when they exist in Morphalou.
        """
        dictionary = get_dictionary()

        def repl(match: re.Match) -> str:
            word = match.group(0)
            if not word.isupper():
                return word
            accented = dictionary.accentize(word)
            return accented or word

        return WORD_PATTERN.sub(repl, text)
