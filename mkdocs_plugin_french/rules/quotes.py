from __future__ import annotations

import re
from .base import RuleDefinition, RuleResult, regex_finditer
from ..constants import NNBSP

RE_ASCII_QUOTES = re.compile(r'"([^"\n]+)"')


def det_quotes(text: str) -> list[RuleResult]:
    return regex_finditer(
        text,
        RE_ASCII_QUOTES,
        lambda m: f'Guillemets anglais → français « … » : "{m.group(1)}"',
        lambda m: f"«{NNBSP}{m.group(1)}{NNBSP}»",
    )


def fix_quotes(text: str) -> str:
    return RE_ASCII_QUOTES.sub(r"«" + NNBSP + r"\1" + NNBSP + "»", text)


RULE = RuleDefinition(
    name="quotes",
    config_attr="quotes",
    detector=det_quotes,
    fixer=fix_quotes,
)
