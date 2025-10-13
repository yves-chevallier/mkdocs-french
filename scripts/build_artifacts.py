from __future__ import annotations

from mkdocs_french.artifacts import default_data_path
from mkdocs_french.artifacts.build import build_morphalou_artifact


def main() -> None:
    target = default_data_path()
    build_morphalou_artifact(target, force=True, quiet=False)
    if not target.exists():
        raise SystemExit(f"Expected artifact {target} to exist after build.")


if __name__ == "__main__":
    main()
