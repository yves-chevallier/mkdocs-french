"""Rule that converts straight double quotes to French guillemets."""

from __future__ import annotations

import re

from ..constants import NNBSP
from .base import Rule, RuleResult, regex_finditer


RE_ASCII_QUOTES = re.compile(r'"([^"\n]+)"')


class QuotesRule(Rule):
    """Replace ASCII quotes with French guillemets and narrow spacing."""

    def __init__(self) -> None:
        """Register the rule in the orchestrator."""
        super().__init__(name="quotes", config_attr="quotes")

    def detect(self, text: str) -> list[RuleResult]:
        """Return warnings for straight double quotes.

        Args:
            text: Text fragment to scan.

        Returns:
            A list of rule results suggesting the guillemet replacement along
            with a preview of the fixed snippet.
        """
        return regex_finditer(
            text,
            RE_ASCII_QUOTES,
            lambda m: f'Guillemets anglais → français « … » : "{m.group(1)}"',
            lambda m: f"«{NNBSP}{m.group(1)}{NNBSP}»",
        )

    def fix(self, text: str) -> str:
        """Swap straight quotes for « … » with narrow non-breaking spaces.

        Args:
            text: Text fragment to transform.

        Returns:
            The text updated with the typographically correct guillemets.
        """
        return RE_ASCII_QUOTES.sub(r"«" + NNBSP + r"\1" + NNBSP + "»", text)
