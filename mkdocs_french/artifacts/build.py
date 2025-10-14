"""Utilities to build and serialize the bundled Morphalou artifact."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import sys
from typing import Iterable, Mapping

from ..dictionary import LISTING_URL, ZIP_PATTERN, Dictionary
from . import SCHEMA_VERSION, default_data_path


def build_morphalou_artifact(
    output_path: Path | None = None, *, force: bool = False, quiet: bool = False
) -> Path:
    """Build the compressed Morphalou artifact ready to be versioned.

    Args:
        output_path: Target path. Defaults to ``artifacts/morphalou_data.json.gz``.
        force: Whether to overwrite existing files.
        quiet: Reduce messages printed to stderr.

    Returns:
        Path to the generated artifact.

    Raises:
        FileExistsError: If the target exists and ``force`` is ``False``.
    """
    target = output_path or default_data_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists() and not force:
        raise FileExistsError(
            f"L'artéfact {target} existe déjà. Utilisez --force pour le régénérer."
        )

    dictionary = Dictionary(use_static_data=False)
    try:
        if not quiet:
            print("Downloading and preparing Morphalou…", file=sys.stderr)
        dictionary.prepare()
    finally:
        dictionary.cleanup()

    payload = _serialize_dictionary(dictionary)
    if not quiet:
        print(
            f"Writing {target.name} with {len(payload['words'])} entries…",
            file=sys.stderr,
        )
    _write_gz_json(target, payload)
    return target


def _serialize_dictionary(dictionary: Dictionary) -> dict:
    """Convert a :class:`Dictionary` into a JSON-serializable mapping.

    Args:
        dictionary: Source dictionary whose indexes have been prepared.

    Returns:
        Mapping ready to be dumped as JSON.
    """
    words = sorted(dictionary.words)
    ligature_map = dictionary._ligature_map.copy()
    accent_map = {k: list(v) for k, v in dictionary._accent_map.items()}

    return {
        "schema_version": SCHEMA_VERSION,
        "normalized": True,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "source": {"listing_url": LISTING_URL, "zip_pattern": ZIP_PATTERN.pattern},
        "stats": {
            "word_count": len(words),
            "ligature_entries": len(ligature_map),
            "accent_entries": len(accent_map),
        },
        "words": words,
        "ligature_map": ligature_map,
        "accent_map": accent_map,
    }


def _write_gz_json(path: Path, payload: Mapping[str, object]) -> None:
    """Write the given payload as UTF-8 JSON compressed with gzip.

    Args:
        path: Destination file path.
        payload: JSON-serializable mapping to serialize.
    """
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    with gzip.open(path, mode="wb") as handle:
        handle.write(data)


def main(argv: Iterable[str] | None = None) -> int:
    """Command-line interface for building the Morphalou artifact.

    Args:
        argv: Optional sequence overriding ``sys.argv``.

    Returns:
        Process exit code (zero on success).
    """
    parser = argparse.ArgumentParser(
        prog="mkdocs-french build",
        description="Generate the Morphalou artifact for mkdocs-plugin-french.",
    )
    parser.add_argument(
        "--output", type=Path, help="Custom destination path for the generated file."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the existing artifact if present.",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress most progress messages."
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        target = build_morphalou_artifact(
            args.output, force=args.force, quiet=args.quiet
        )
    except Exception as exc:  # pragma: no cover - CLI
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"Generated artifact: {target}")
    return 0


if __name__ == "__main__":  # pragma: no cover - direct execution
    raise SystemExit(main())
