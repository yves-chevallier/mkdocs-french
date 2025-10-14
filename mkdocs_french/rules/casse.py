"""Rule that enforces lowercase words for months, days, languages, and countries."""

from __future__ import annotations

import re

from .base import Rule, RuleResult


MOIS = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

LANGS = [
    "français",
    "anglais",
    "espagnol",
    "allemand",
    "italien",
    "portugais",
    "néerlandais",
    "chinois",
    "japonais",
    "arabe",
    "russe",
]

COUNTRIES = [
    "France",
    "Suisse",
    "Allemagne",
    "Italie",
    "Espagne",
    "Portugal",
    "Belgique",
    "Luxembourg",
    "États-Unis",
    "Royaume-Uni",
]

LOWERCASE_WORDS = MOIS + JOURS + LANGS
COUNTRY_PATTERNS = [
    (target, re.compile(rf"(?<!\w){re.escape(target)}(?!\w)", re.IGNORECASE))
    for target in COUNTRIES
]


def _is_sentence_start(text: str, index: int) -> bool:
    """Return whether the match index is at the beginning of a sentence.

    Args:
        text: Full string being processed.
        index: Zero-based index where the match starts.

    Returns:
        ``True`` if the index appears to begin a sentence, ``False`` otherwise.

    Examples:
        >>> from mkdocs_french.rules.casse import _is_sentence_start
        >>> _is_sentence_start("Hello. World", 7)
        True
        >>> _is_sentence_start("hello World", 6)
        False
    """
    pos = index - 1
    while pos >= 0 and text[pos].isspace():
        pos -= 1
    if pos < 0:
        return True
    return text[pos] in ".!?:("


class CasseRule(Rule):
    """Normalize casing for common French words that should remain lowercase."""

    def __init__(self) -> None:
        """Register the rule in the orchestrator."""
        super().__init__(name="casse", config_attr="casse")

    def detect(self, text: str) -> list[RuleResult]:
        """Return warnings for capitalized words that should remain lowercase.

        Args:
            text: Text fragment to inspect.

        Returns:
            A list of rule results where the preview contains the lowercase form.
        """
        res: list[RuleResult] = []
        for word in LOWERCASE_WORDS:
            pattern = re.compile(rf"\b{word.capitalize()}\b")
            for match in pattern.finditer(text):
                if _is_sentence_start(match.string, match.start()):
                    continue
                res.append(
                    (
                        match.start(),
                        match.end(),
                        f"Casse incorrecte pour «{match.group(0)}»",
                        word,
                    )
                )
        for target, pattern in COUNTRY_PATTERNS:
            for match in pattern.finditer(text):
                if match.group(0) == target:
                    continue
                res.append(
                    (
                        match.start(),
                        match.end(),
                        f"Casse incorrecte pour le pays «{match.group(0)}»",
                        target,
                    )
                )
        return res

    def fix(self, text: str) -> str:
        """Rewrite text so that targeted words use their canonical casing.

        Args:
            text: Text fragment to mutate.

        Returns:
            The corrected string with the enforced lowercase or proper country casing.
        """
        for word in LOWERCASE_WORDS:
            pattern = re.compile(rf"\b{word.capitalize()}\b")

            def lower_replacer(match: re.Match) -> str:
                if _is_sentence_start(match.string, match.start()):
                    return match.group(0)
                return word

            text = pattern.sub(lower_replacer, text)
        for target, pattern in COUNTRY_PATTERNS:
            text = pattern.sub(lambda _m, t=target: t, text)
        return text
