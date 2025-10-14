from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, List, Optional, Tuple


RuleResult = Tuple[int, int, str, Optional[str]]


@dataclass(frozen=True)
class RuleDefinition:
    """Structure de base pour déclarer une règle typographique."""

    name: str
    config_attr: str
    detector: Callable[[str], List[RuleResult]]
    fixer: Callable[[str], str]


def regex_finditer(
    text: str,
    pattern: re.Pattern,
    make_msg: Callable[[re.Match], str],
    replacement_preview: Callable[[re.Match], Optional[str]] | None = None,
) -> List[RuleResult]:
    """Utilitaire commun pour collecter les occurrences regex."""
    out: List[RuleResult] = []
    for match in pattern.finditer(text):
        preview = replacement_preview(match) if replacement_preview else None
        out.append((match.start(), match.end(), make_msg(match), preview))
    return out
