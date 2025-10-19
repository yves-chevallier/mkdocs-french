"""Convenience imports and factories for the built-in French typography rules."""

from .abbreviation import AbbreviationRule
from .base import Rule, RuleResult
from .casse import CasseRule
from .diacritics import DiacriticsRule
from .ligatures import LigaturesRule
from .orchestrator import RuleOrchestrator, RuleWarning
from .ordinaux import OrdinauxRule
from .quotes import QuotesRule
from .spacing import SpacingRule
from .units import UnitsRule


def build_markdown_rules() -> tuple[Rule, ...]:
    """Return rules applied while processing Markdown sources."""

    return (
        AbbreviationRule(),
        CasseRule(),
        DiacriticsRule(),
    )


def build_html_rules() -> tuple[Rule, ...]:
    """Return rules applied while processing rendered HTML."""

    return (
        OrdinauxRule(),
        LigaturesRule(),
        SpacingRule(),
        QuotesRule(),
        UnitsRule(),
    )


def build_rules() -> tuple[Rule, ...]:
    """Return the full rule chain as used historically."""

    return build_markdown_rules() + build_html_rules()


ALL_RULES = build_rules()

__all__ = [
    "Rule",
    "RuleResult",
    "RuleWarning",
    "RuleOrchestrator",
    "build_markdown_rules",
    "build_html_rules",
    "ALL_RULES",
    "build_rules",
]
