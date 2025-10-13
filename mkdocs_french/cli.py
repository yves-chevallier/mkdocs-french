from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from .artifacts.build import build_morphalou_artifact


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mkdocs-french",
        description="Auxiliary tooling for mkdocs-plugin-french.",
    )
    subparsers = parser.add_subparsers(dest="command")

    _configure_build_parser(subparsers)

    args = parser.parse_args(list(argv) if argv is not None else None)

    if not getattr(args, "handler", None):
        parser.print_help(sys.stderr)
        return 1

    return args.handler(args)


def _configure_build_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    build_parser = subparsers.add_parser(
        "build",
        help="Generate the compressed Morphalou artifacts.",
    )
    build_parser.add_argument(
        "--output",
        type=Path,
        help="Destination path (defaults to mkdocs_french/artifacts).",
    )
    build_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the existing file if it already exists.",
    )
    build_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Silence progress messages.",
    )
    build_parser.set_defaults(handler=_run_build)


def _run_build(args: argparse.Namespace) -> int:
    try:
        target = build_morphalou_artifact(
            args.output,
            force=args.force,
            quiet=args.quiet,
        )
    except Exception as exc:  # pragma: no cover - CLI
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"Generated artifact: {target}")
    return 0
