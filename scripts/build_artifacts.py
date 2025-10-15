"""Helper script used by build hooks to regenerate Morphalou artifacts."""

from __future__ import annotations

from pathlib import Path
import sys


def _ensure_src_on_path() -> None:
    """Add the project root to ``sys.path`` during Poetry build hooks."""

    project_root = Path(__file__).resolve().parents[1]
    # ``poetry build`` runs this script from an isolated environment where the
    # project is not yet installed.  Importing the package would fail unless we
    # explicitly add the source tree to ``sys.path``.
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def main() -> None:
    """Regenerate the Morphalou artifact in-place.

    Raises:
        SystemExit: If the artifact was not produced as expected.
    """
    _ensure_src_on_path()

    # These imports must happen after sys.path has been patched for Poetry build hooks.
    from mkdocs_french.artifacts import default_data_path
    from mkdocs_french.artifacts.build import build_morphalou_artifact

    target = default_data_path()
    build_morphalou_artifact(target, force=True, quiet=False)
    if not target.exists():
        raise SystemExit(f"Expected artifact {target} to exist after build.")


if __name__ == "__main__":
    main()
