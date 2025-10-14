"""Coordinate execution of typographic rules with warning collection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Sequence, Tuple

from .base import Rule


@dataclass(frozen=True)
class RuleWarning:
    """Diagnostic returned when a rule reports a warning.

    Attributes:
        rule: Rule that produced the warning.
        start: Start index within the processed text.
        end: End index within the processed text.
        message: Human-readable explanation of the issue.
        preview: Optional preview of the proposed fix.
    """

    rule: Rule
    start: int
    end: int
    message: str
    preview: str | None


class RuleOrchestrator:
    """Coordinate the sequential application of typographic rules."""

    def __init__(self, rules: Sequence[Rule]) -> None:
        """Store the rule list for later processing.

        Args:
            rules: Iterable of rule instances to apply in order.
        """
        self._rules: Tuple[Rule, ...] = tuple(rules)

    @property
    def rules(self) -> Tuple[Rule, ...]:
        """Tuple of rules managed by the orchestrator."""
        return self._rules

    def process(
        self,
        text: str,
        level_lookup: Callable[[Rule], object],
    ) -> tuple[str, List[RuleWarning]]:
        """Apply rules according to their configured severity level.

        Args:
            text: Input string to process.
            level_lookup: Callable mapping a rule to its severity level (ignore,
                warn, or fix).

        Returns:
            A tuple containing the possibly mutated text and a list of warnings
            generated while processing in ``warn`` mode.

        Examples:
            >>> from mkdocs_french.rules.spacing import SpacingRule
            >>> orchestrator = RuleOrchestrator((SpacingRule(),))
            >>> def level(rule):
            ...     return "fix"
            >>> cleaned, warnings = orchestrator.process("Bonjour! ", level)
            >>> cleaned.endswith("! ")
            False
            >>> warnings
            []
        """
        current = text
        warnings: List[RuleWarning] = []

        for rule in self._rules:
            level = level_lookup(rule)
            level_value = getattr(level, "value", level)

            if level_value == "ignore":
                continue
            if level_value == "warn":
                for start, end, message, preview in rule.detect(current):
                    warnings.append(
                        RuleWarning(
                            rule=rule,
                            start=start,
                            end=end,
                            message=message,
                            preview=preview,
                        )
                    )
                continue

            current = rule.fix(current)

        return current, warnings
