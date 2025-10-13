"""Public package exports for ``mkdocs_french``."""

from __future__ import annotations

from .cli import main
from .plugin import FrenchPlugin, Level

__all__ = ["FrenchPlugin", "Level", "main"]
