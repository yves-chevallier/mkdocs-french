r"""Shared abstractions and helpers for typographic rules.

This module defines the :class:`Rule` base class used by every concrete rule as
well as a small regex helper to build consistent warning payloads.

Typical usage:
    >>> import re
    >>> from mkdocs_french.rules.base import regex_finditer
    >>> matches = regex_finditer("Hello  world", re.compile(r"\s{2,}"), lambda m: "collapse space")
    >>> matches
    [(5, 7, 'collapse space', None)]
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import re
from typing import Callable, List, Optional, Tuple


RuleResult = Tuple[int, int, str, Optional[str]]


class Rule(ABC):
    """Abstract base class for every typographic rule in the plugin."""

    name: str
    config_attr: str

    def __init__(self, name: str, config_attr: str) -> None:
        """Initialize a rule.

        Args:
            name: Human readable identifier for the rule.
            config_attr: Name of the configuration attribute that controls the rule.
        """
        self.name = name
        self.config_attr = config_attr

    @abstractmethod
    def detect(self, text: str) -> List[RuleResult]:
        """Return non-blocking findings for the provided text.

        Args:
            text: Raw HTML or Markdown fragment to inspect.

        Returns:
            A list of tuples describing issues. The tuple contains the start
            index, end index, message, and an optional preview string.
        """
        raise NotImplementedError

    @abstractmethod
    def fix(self, text: str) -> str:
        """Return a corrected version of the provided text.

        Args:
            text: Raw HTML or Markdown fragment to transform.

        Returns:
            The amended text once the rule has applied the necessary fixes.
        """
        raise NotImplementedError


def regex_finditer(
    text: str,
    pattern: re.Pattern,
    make_msg: Callable[[re.Match], str],
    replacement_preview: Callable[[re.Match], Optional[str]] | None = None,
) -> List[RuleResult]:
    """Collect regex occurrences and standardize them into rule results.

    Args:
        text: The string in which to look for matches.
        pattern: Compiled regular expression used for detection.
        make_msg: Callable building the warning message from a match object.
        replacement_preview: Optional callable returning the preview string for
            the detected match. When not provided, the preview field is ``None``.

    Returns:
        A list of tuples describing each match ready to be consumed by the rule
        orchestrator.
    """
    out: List[RuleResult] = []
    for match in pattern.finditer(text):
        preview = replacement_preview(match) if replacement_preview else None
        out.append((match.start(), match.end(), make_msg(match), preview))
    return out
