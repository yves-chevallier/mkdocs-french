from __future__ import annotations

import re
from typing import List, Tuple

from .base import RuleDefinition, RuleResult
from ..constants import NBSP, NNBSP

SI_PREFIXES = [
    "Y",
    "Z",
    "E",
    "P",
    "T",
    "G",
    "M",
    "k",
    "h",
    "da",
    "d",
    "c",
    "m",
    "µ",
    "u",
    "n",
    "p",
    "f",
    "a",
    "z",
    "y",
]

PREFIXED_BASE_UNITS = {
    "m",
    "g",
    "s",
    "A",
    "K",
    "mol",
    "cd",
    "Hz",
    "N",
    "Pa",
    "J",
    "W",
    "C",
    "V",
    "F",
    "Ω",
    "Ohm",
    "S",
    "Wb",
    "T",
    "H",
    "L",
    "l",
    "B",
    "bit",
}

NON_PREFIXED_UNITS = {
    "%",
    "‰",
    "ppm",
    "ppb",
    "°C",
    "°F",
    "°",
    "rad",
    "sr",
    "min",
    "h",
    "bar",
    "atm",
    "mmHg",
    "Pa",
    "dB",
    "g",
    "kg",
    "L",
    "mL",
    "kWh",
    "Wh",
}

CURRENCY_UNITS = {"€", "$", "£", "¥", "CHF", "CAD", "USD"}


def build_unit_patterns(prefixed_units: set[str]) -> Tuple[re.Pattern, List[str]]:
    units: set[str] = set()
    units.update(prefixed_units)
    units.update(NON_PREFIXED_UNITS)
    units.update(CURRENCY_UNITS)
    sorted_units = sorted(units, key=len, reverse=True)
    escaped_units = [re.escape(u) for u in sorted_units]
    pattern = re.compile(
        rf"(?P<number>(?<!\w)\d+(?:[.,]\d+)?)(?P<sep>[\s\u00A0\u202F]*)"
        rf"(?P<unit>(?:{'|'.join(escaped_units)}))(?![\w%°])"
    )
    return pattern, sorted_units


PREFIXED_UNITS_EXPANDED: set[str] = set()
for base in PREFIXED_BASE_UNITS:
    PREFIXED_UNITS_EXPANDED.add(base)
    for prefix in SI_PREFIXES:
        PREFIXED_UNITS_EXPANDED.add(prefix + base)

UNIT_PATTERN, SORTED_UNITS = build_unit_patterns(PREFIXED_UNITS_EXPANDED)


def det_units(text: str) -> list[RuleResult]:
    results: List[RuleResult] = []
    for match in UNIT_PATTERN.finditer(text):
        sep = match.group("sep")
        if NBSP in sep or NNBSP in sep:
            continue
        number = match.group("number")
        unit = match.group("unit")
        start, end = match.span()
        preview = f"{number}{NNBSP}{unit}"
        results.append(
            (start, end, f"Unités : «{match.group(0)}» → «{preview}»", preview)
        )
    return results


def fix_units(text: str) -> str:
    def repl(match: re.Match) -> str:
        number = match.group("number")
        unit = match.group("unit")
        return f"{number}{NNBSP}{unit}"

    return UNIT_PATTERN.sub(repl, text)


RULE = RuleDefinition(
    name="units",
    config_attr="units",
    detector=det_units,
    fixer=fix_units,
)
