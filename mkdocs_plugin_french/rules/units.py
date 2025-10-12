from __future__ import annotations

import re
from .base import RuleDefinition, RuleResult, regex_finditer

RE_NUM_KG = re.compile(r"(\d)\s*kg\b", re.I)
RE_NUM_PCT = re.compile(r"(\d)\s*%")
RE_NUM_EURO = re.compile(r"(\d)\s*€")
RE_CELSIUS = re.compile(r"(\d)\s*°\s*C", re.I)
RE_TIME = re.compile(r"(\d)\s*h\s*(\d{2})\b")


def det_units(text: str) -> list[RuleResult]:
    res: list[RuleResult] = []
    res += regex_finditer(
        text,
        RE_NUM_KG,
        lambda m: "Unités : «10kg» → «10 kg»",
        lambda m: f"{m.group(1)} kg",
    )
    res += regex_finditer(
        text,
        RE_NUM_PCT,
        lambda m: "Unités : «10%» → «10 %»",
        lambda m: f"{m.group(1)} %",
    )
    res += regex_finditer(
        text,
        RE_NUM_EURO,
        lambda m: "Unités : «10€» → «10 €»",
        lambda m: f"{m.group(1)} €",
    )
    res += regex_finditer(
        text,
        RE_CELSIUS,
        lambda m: "Unités : «10°C» → «10 °C»",
        lambda m: f"{m.group(1)} °C",
    )
    res += regex_finditer(
        text,
        RE_TIME,
        lambda m: "Heure : «14h30» → «14 h 30»",
        lambda m: f"{m.group(1)} h {m.group(2)}",
    )
    return res


def fix_units(text: str) -> str:
    text = RE_NUM_KG.sub(r"\1 kg", text)
    text = RE_NUM_PCT.sub(r"\1 %", text)
    text = RE_NUM_EURO.sub(r"\1 €", text)
    text = RE_CELSIUS.sub(r"\1 °C", text)
    text = RE_TIME.sub(r"\1 h \2", text)
    return text


RULE = RuleDefinition(
    name="units",
    config_attr="units",
    detector=det_units,
    fixer=fix_units,
)

