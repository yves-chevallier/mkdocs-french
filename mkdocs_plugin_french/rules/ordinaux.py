from __future__ import annotations

import re
from .base import RuleDefinition, RuleResult, regex_finditer

_ORD_1ER = re.compile(r"\b1(?:\^?er)\b", re.I)
_ORD_1RE = re.compile(r"\b1(?:\^?re|ère)\b", re.I)
_ORD_EME = re.compile(r"\b([2-9]|[1-9]\d+)\s*(?:\^?e?me|\^?ème|\^?eme)\b", re.I)


def det_ordinaux(text: str) -> list[RuleResult]:
    out: list[RuleResult] = []
    out += regex_finditer(
        text, _ORD_1RE, lambda m: f"Ordinal «{m.group(0)}» → «1re»", lambda m: "1re"
    )
    out += regex_finditer(
        text,
        _ORD_1ER,
        lambda m: f"Vérifier «{m.group(0)}» (ok «1er» ; parfois «1re»).",
        lambda m: "1er",
    )
    out += regex_finditer(
        text,
        _ORD_EME,
        lambda m: f"Ordinal «{m.group(0)}» → «{m.group(1)}e»",
        lambda m: f"{m.group(1)}e",
    )
    return out


def fix_ordinaux(text: str) -> str:
    text = _ORD_1RE.sub("1re", text)
    text = _ORD_1ER.sub("1er", text)
    text = _ORD_EME.sub(lambda m: f"{m.group(1)}e", text)
    return text


RULE = RuleDefinition(
    name="ordinaux",
    config_attr="ordinaux",
    detector=det_ordinaux,
    fixer=fix_ordinaux,
)

