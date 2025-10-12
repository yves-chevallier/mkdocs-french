from __future__ import annotations

import re
from .base import RuleDefinition, RuleResult

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
    pos = index - 1
    while pos >= 0 and text[pos].isspace():
        pos -= 1
    if pos < 0:
        return True
    return text[pos] in ".!?:("


def det_casse(text: str) -> list[RuleResult]:
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


def fix_casse(text: str) -> str:
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


RULE = RuleDefinition(
    name="casse",
    config_attr="casse",
    detector=det_casse,
    fixer=fix_casse,
)
