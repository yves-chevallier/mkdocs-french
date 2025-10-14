"""Rules ensuring proper spacing around measurement and currency units."""

from __future__ import annotations

import re
from typing import List, Tuple

from ..constants import NBSP, NNBSP
from .base import Rule, RuleResult


# fmt: off
SI_PREFIXES = [
    "Y", "Z", "E", "P", "T", "G", "M", "k", "h", "da",
    "d", "c", "m", "µ", "u", "n", "p", "f", "a", "z", "y",
]

PREFIXED_BASE_UNITS = {
    "m", "g", "s", "A", "K", "mol", "cd", "Hz", "N", "Pa",
    "J", "W", "C", "V", "F", "Ω", "Ohm", "S", "Wb", "T", "H",
    "L", "l", "B", "bit",
}

NON_PREFIXED_UNITS = {
    "%", "‰", "ppm", "ppb", "°C", "°F", "°", "rad", "sr",
    "min", "h", "bar", "atm", "mmHg", "Pa", "dB", "g", "kg",
    "L", "mL", "kWh", "Wh",
}
# fmt: on

CURRENCY_UNITS = {"€", "$", "£", "¥", "CHF", "CAD", "USD"}


def build_unit_patterns(prefixed_units: set[str]) -> Tuple[re.Pattern, List[str]]:
    """Build a compiled regex and sorted unit list for detection.

    Args:
        prefixed_units: Set of SI base units optionally prefixed.

    Returns:
        Tuple containing the compiled pattern and the sorted unit list used to
        preserve greedy matching.

    Examples:
        >>> from mkdocs_french.rules.units import build_unit_patterns, PREFIXED_UNITS_EXPANDED
        >>> pattern, units = build_unit_patterns(PREFIXED_UNITS_EXPANDED)
        >>> bool(pattern.search("5kg"))
        True
        >>> units[0] == max(units, key=len)
        True
    """
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


class UnitsRule(Rule):
    """Ensure narrow non-breaking spaces are used with units and currencies."""

    def __init__(self) -> None:
        """Initialize the rule with the registry metadata."""
        super().__init__(name="units", config_attr="units")

    def detect(self, text: str) -> list[RuleResult]:
        """Return warnings for numbers that miss the expected spacing.

        Args:
            text: Text fragment to inspect.

        Returns:
            A list of rule results describing each occurrence lacking the
            narrow non-breaking space between the number and its unit.
        """
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
                (
                    start,
                    end,
                    f"Unités : «{match.group(0)}» → «{preview}»",
                    preview,
                )
            )
        return results

    def fix(self, text: str) -> str:
        """Insert narrow non-breaking spaces between numbers and units.

        Args:
            text: Text fragment to mutate.

        Returns:
            The corrected text where relevant units now use a narrow
            non-breaking space.
        """
        def repl(match: re.Match) -> str:
            number = match.group("number")
            unit = match.group("unit")
            return f"{number}{NNBSP}{unit}"

        return UNIT_PATTERN.sub(repl, text)
