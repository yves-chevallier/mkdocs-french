"""Public package exports for ``mkdocs_french``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .cli import main


if TYPE_CHECKING:  # pragma: no cover - imported only for typing
    from .plugin import FrenchPlugin, Level

__all__ = ["FrenchPlugin", "Level", "main"]


def __getattr__(name: str) -> Any:
    """Lazily import heavy dependencies when accessed as module attributes.

    Args:
        name: Attribute requested via ``getattr``.

    Returns:
        The requested attribute from :mod:`mkdocs_french.plugin`.

    Raises:
        AttributeError: If the attribute does not correspond to a public export.
    """
    if name in {"FrenchPlugin", "Level"}:
        from .plugin import FrenchPlugin, Level

        return {"FrenchPlugin": FrenchPlugin, "Level": Level}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
