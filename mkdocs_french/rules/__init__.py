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


def build_rules() -> tuple[Rule, ...]:
    """Return a freshly instantiated tuple of all default rules.

    Returns:
        Tuple containing new instances of each available rule, ordered to match
        the desired processing chain.
    """
    return (
        AbbreviationRule(),
        OrdinauxRule(),
        LigaturesRule(),
        CasseRule(),
        SpacingRule(),
        QuotesRule(),
        UnitsRule(),
        DiacriticsRule(),
    )


ALL_RULES = build_rules()

__all__ = [
    "Rule",
    "RuleResult",
    "RuleWarning",
    "RuleOrchestrator",
    "ALL_RULES",
    "build_rules",
]
