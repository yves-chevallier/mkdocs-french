"""Rule that replaces ``oe`` and ``ae`` sequences with proper ligatures."""

from __future__ import annotations

import re

from ..dictionary import get_dictionary
from .base import Rule, RuleResult


WORD_PATTERN = re.compile(r"\b[^\W\d_]+\b", re.UNICODE)


def _needs_ligature(word: str) -> bool:
    """Return whether a word contains characters eligible for ligatures.

    Args:
        word: Word to inspect.

    Returns:
        ``True`` when the lowercased word contains ``oe`` or ``ae``.

    Examples:
        >>> from mkdocs_french.rules.ligatures import _needs_ligature
        >>> _needs_ligature("coeur")
        True
        >>> _needs_ligature("chat")
        False
    """
    lowered = word.lower()
    return "oe" in lowered or "ae" in lowered


class LigaturesRule(Rule):
    """Swap eligible digraphs for typographic ligatures using Morphalou."""

    def __init__(self) -> None:
        """Register the rule in the orchestrator."""
        super().__init__(name="ligatures", config_attr="ligatures")

    def detect(self, text: str) -> list[RuleResult]:
        """Return warnings for words that can be ligaturized.

        Args:
            text: Text fragment to inspect.

        Returns:
            A list of rule results where the preview contains the ligatured form.
        """
        results: list[RuleResult] = []
        dictionary = get_dictionary()

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

    def fix(self, text: str) -> str:
        """Apply ligatures directly in the provided text.

        Args:
            text: Text fragment to mutate.

        Returns:
            The corrected text with ``œ`` or ``æ`` ligatures inserted when
            relevant.
        """
        dictionary = get_dictionary()

        def repl(match: re.Match) -> str:
            word = match.group(0)
            if not _needs_ligature(word):
                return word
            return dictionary.ligaturize(word)

        return WORD_PATTERN.sub(repl, text)
