"""Public package exports for ``mkdocs_french``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .cli import main


if TYPE_CHECKING:  # pragma: no cover - imported only for typing
    from .plugin import FrenchPlugin, Level

__all__ = ["FrenchPlugin", "Level", "main"]


def __getattr__(name: str) -> Any:
    """
    Lazily import heavy dependencies.

    ``mkdocs_french.plugin`` pulls in BeautifulSoup during import.  Deferring the
    import prevents Poetry build hooks from failing before runtime dependencies
    are installed.
    """
    if name in {"FrenchPlugin", "Level"}:
        from .plugin import FrenchPlugin, Level

        return {"FrenchPlugin": FrenchPlugin, "Level": Level}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
