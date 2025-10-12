from .base import RuleDefinition, RuleResult  # noqa: F401
from .abbreviation import RULE as ABBREVIATION_RULE
from .ordinaux import RULE as ORDINAUX_RULE
from .ligatures import RULE as LIGATURES_RULE
from .casse import RULE as CASSE_RULE
from .spacing import RULE as SPACING_RULE
from .quotes import RULE as QUOTES_RULE
from .units import RULE as UNITS_RULE

ALL_RULES = [
    ABBREVIATION_RULE,
    ORDINAUX_RULE,
    LIGATURES_RULE,
    CASSE_RULE,
    SPACING_RULE,
    QUOTES_RULE,
    UNITS_RULE,
]

__all__ = ["RuleDefinition", "RuleResult", "ALL_RULES"]
