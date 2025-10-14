from __future__ import annotations

import re

from .base import RuleDefinition, RuleResult, regex_finditer


_ABBR_BAD = re.compile(r"\b(c\s*[-\.]?\s*a\s*[-\.]?\s*d)\b", re.I)
_ABBR_PEX = re.compile(r"\b(p\s*\.?\s*ex)\b\.?", re.I)
_ABBR_NB = re.compile(r"\b(n\s*\.?\s*b)\b\.?", re.I)
_ETC_BAD = re.compile(r"\b(?P<word>etc)(?:\s*\.(?:\s*\.)+|\s*…+)(?=\W|$)", re.I)


def _etc_replacement(word: str) -> str:
    if word.isupper():
        return "ETC."
    if word[0].isupper():
        return "Etc."
    return "etc."


def det_abbreviation(text: str) -> list[RuleResult]:
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


def fix_abbreviation(text: str) -> str:
    text = _ABBR_BAD.sub("c.-à-d.", text)
    text = _ABBR_PEX.sub("p. ex.", text)
    text = _ABBR_NB.sub("N. B.", text)
    text = _ETC_BAD.sub(lambda m: _etc_replacement(m.group("word")), text)
    return text


RULE = RuleDefinition(
    name="abbreviation",
    config_attr="abbreviation",
    detector=det_abbreviation,
    fixer=fix_abbreviation,
)
