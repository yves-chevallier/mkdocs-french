"""Rule enforcing consistent French abbreviations and ellipsis usage."""

from __future__ import annotations


import re

from .base import Rule, RuleResult, regex_finditer


_ABBR_BAD = re.compile(r"\b(c\s*[-\.]?\s*a\s*[-\.]?\s*d)\b", re.I)
_ABBR_PEX = re.compile(r"\b(p\s*\.?\s*ex)\b\.?", re.I)
_ABBR_NB = re.compile(r"\b(n\s*\.?\s*b)\b\.?", re.I)
_ETC_BAD = re.compile(r"\b(?P<word>etc)(?:\s*\.(?:\s*\.)+|\s*…+)(?=\W|$)", re.I)


def _etc_replacement(word: str) -> str:
    """Return the corrected casing and punctuation for ``etc``.

    Args:
        word: Raw match for the ``etc`` token, preserving the original casing.

    Returns:
        The properly cased version followed by a full stop.

    Examples:
        >>> from mkdocs_french.rules.abbreviation import _etc_replacement
        >>> _etc_replacement("etc")
        'etc.'
        >>> _etc_replacement("Etc")
        'Etc.'
        >>> _etc_replacement("ETC")
        'ETC.'
    """
    if word.isupper():
        return "ETC."
    if word[0].isupper():
        return "Etc."
    return "etc."


class AbbreviationRule(Rule):
    """Normalize key abbreviations such as ``c.-à-d.`` and ``p. ex.``."""

    def __init__(self) -> None:
        """Register the rule in the orchestrator."""
        super().__init__(name="abbreviation", config_attr="abbreviation")

    def detect(self, text: str) -> list[RuleResult]:
        """Return warnings for malformed abbreviations.

        Args:
            text: Text fragment to inspect.

        Returns:
            A list of rule results containing the start/end position, a message,
            and the suggested replacement for each issue.
        """
        results: list[RuleResult] = []
        results += regex_finditer(
            text,
            _ABBR_BAD,
            lambda m: f"Abréviation mauvaise : «{m.group(0)}» ; attendu «c.-à-d.»",
            lambda m: "c.-à-d.",
        )
        results += regex_finditer(
            text,
            _ABBR_PEX,
            lambda m: f"Abréviation : «{m.group(0)}» ; attendu «p. ex.»",
            lambda m: "p. ex.",
        )
        results += regex_finditer(
            text,
            _ABBR_NB,
            lambda m: f"Abréviation : «{m.group(0)}» ; attendu «N. B.»",
            lambda m: "N. B.",
        )
        results += regex_finditer(
            text,
            _ETC_BAD,
            lambda m: f"Ponctuation superflue après «{m.group(0)}» ; utiliser «{_etc_replacement(m.group('word'))}»",
            lambda m: _etc_replacement(m.group("word")),
        )
        return results

    def fix(self, text: str) -> str:
        """Rewrite abbreviations using the canonical French typography.

        Args:
            text: Text fragment to transform.

        Returns:
            The updated string with corrected abbreviations and ellipsis usage.
        """
        text = _ABBR_BAD.sub("c.-à-d.", text)
        text = _ABBR_PEX.sub("p. ex.", text)
        text = _ABBR_NB.sub("N. B.", text)
        text = _ETC_BAD.sub(lambda m: _etc_replacement(m.group("word")), text)
        return text
