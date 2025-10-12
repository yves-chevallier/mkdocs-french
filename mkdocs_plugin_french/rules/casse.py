from __future__ import annotations

import re
from .base import RuleDefinition, RuleResult, regex_finditer

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


def det_casse(text: str) -> list[RuleResult]:
    res: list[RuleResult] = []
    for word in MOIS + JOURS + LANGS:
        pattern = re.compile(rf"\b{word.capitalize()}\b")
        res += regex_finditer(
            text,
            pattern,
            lambda m, base=word: f"Casse : «{m.group(0)}» → «{base}»",
            lambda m, base=word: base,
        )
    return res


def fix_casse(text: str) -> str:
    for word in MOIS + JOURS + LANGS:
        text = re.sub(rf"\b{word.capitalize()}\b", word, text)
    return text


RULE = RuleDefinition(
    name="casse",
    config_attr="casse",
    detector=det_casse,
    fixer=fix_casse,
)

