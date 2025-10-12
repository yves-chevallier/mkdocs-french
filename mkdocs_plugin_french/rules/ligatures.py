from __future__ import annotations

import re
from .base import RuleDefinition, RuleResult, regex_finditer

LIG_DICT = {
    "coeur": "cœur",
    "soeur": "sœur",
    "boeuf": "bœuf",
    "coelacanthe": "cœlacanthe",
    "noeud": "nœud",
    "oeil": "œil",
    "oeuf": "œuf",
    "oeuvre": "œuvre",
    "oeuvrer": "œuvrer",
    "oedeme": "œdème",
    "oesophage": "œsophage",
    "oestrogène": "œstrogène",
    "oecuménique": "œcuménique",
    "oeillet": "œillet",
    "foetus": "fœtus",
    "oedipe": "œdipe",
    "caecum": "cæcum",
    "tænia": "tænia",
    "vitae": "vitæ",
    "ex aequo": "ex æquo",
    "cænotype": "cænotype",
    "voeu": "vœu",
}


def det_ligatures(text: str) -> list[RuleResult]:
    results: list[RuleResult] = []
    for plain, lig in LIG_DICT.items():
        pattern = re.compile(rf"\b{plain}\b", re.I)
        results += regex_finditer(
            text,
            pattern,
            lambda m, l=lig: f"Ligature : «{m.group(0)}» → «{l}»",
            lambda m, l=lig: l,
        )
    return results


def fix_ligatures(text: str) -> str:
    for plain, lig in LIG_DICT.items():
        text = re.sub(rf"\b{plain}\b", lig, text, flags=re.I)
    return text


RULE = RuleDefinition(
    name="ligatures",
    config_attr="ligatures",
    detector=det_ligatures,
    fixer=fix_ligatures,
)

