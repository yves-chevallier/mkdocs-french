"""Console entry point for ``python -m mkdocs_french``."""

from __future__ import annotations

from .cli import main


if __name__ == "__main__":  # pragma: no cover - exercised via CLI entry
    raise SystemExit(main())
