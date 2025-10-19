"""Command-line entry point for mkdocs-french helper utilities."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Iterable, List, Sequence, Tuple

from .constants import DEFAULT_ADMONITION_TRANSLATIONS
from .plugin import FrenchPlugin, Level, make_plugin_config

from .artifacts.build import build_morphalou_artifact


_COMMENT_DIRECTIVE_RE = re.compile(
    r"<!--\s*(?P<closing>/)?fr-typo-ignore(?:(?:-(?P<variant>start|end)))?\s*-->",
    re.IGNORECASE,
)


@dataclass
class _Segment:
    text: str
    ignored: bool


def main(argv: Iterable[str] | None = None) -> int:
    """Execute the command-line interface.

    Args:
        argv: Optional iterable overriding ``sys.argv``.

    Returns:
        Exit code (zero on success, non-zero on error or misuse).
    """
    parser = argparse.ArgumentParser(
        prog="mkdocs-french", description="Auxiliary tooling for mkdocs-plugin-french."
    )
    subparsers = parser.add_subparsers(dest="command")

    _configure_build_parser(subparsers)
    _configure_check_parser(subparsers)
    _configure_fix_parser(subparsers)

    args = parser.parse_args(list(argv) if argv is not None else None)

    if not getattr(args, "handler", None):
        parser.print_help(sys.stderr)
        return 1

    return args.handler(args)


def _configure_build_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the ``build`` sub-command on the provided subparsers object.

    Args:
        subparsers: Sub-parser factory returned by ``ArgumentParser.add_subparsers``.
    """
    build_parser = subparsers.add_parser(
        "build", help="Generate the compressed Morphalou artifacts."
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
        "--quiet", action="store_true", help="Silence progress messages."
    )
    build_parser.set_defaults(handler=_run_build)


def _run_build(args: argparse.Namespace) -> int:
    """Run the ``build`` sub-command and return an exit code.

    Args:
        args: Parsed arguments produced by the CLI.

    Returns:
        Exit code signaling success or failure.
    """
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


def _configure_check_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the ``check`` sub-command displaying pending corrections."""

    check_parser = subparsers.add_parser(
        "check",
        help="List Markdown corrections that would be applied by mkdocs-french.",
    )
    check_parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("docs"),
        help="Directory containing Markdown sources (default: docs).",
    )
    check_parser.set_defaults(handler=_run_check)


def _configure_fix_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the ``fix`` sub-command mutating Markdown sources in-place."""

    fix_parser = subparsers.add_parser(
        "fix", help="Rewrite Markdown files with mkdocs-french corrections applied."
    )
    fix_parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("docs"),
        help="Directory containing Markdown sources (default: docs).",
    )
    fix_parser.set_defaults(handler=_run_fix)


def _run_check(args: argparse.Namespace) -> int:
    """Display the corrections that would be applied without modifying files."""

    docs_dir: Path = args.docs_dir
    if not docs_dir.exists():
        print(f"Directory not found: {docs_dir}", file=sys.stderr)
        return 1

    issues_found = False
    for path in _iter_markdown_files(docs_dir):
        plugin = _build_cli_plugin()
        original = path.read_text(encoding="utf-8")
        issues, _ = _analyze_markdown(original, plugin)
        if not issues:
            continue

        issues_found = True
        rel_path = _format_relative(path)
        print(f"{rel_path}:")
        for issue in issues:
            line_display = issue["line"] if issue["line"] is not None else "—"
            preview = issue.get("preview")
            preview_txt = f" → «{preview}»" if preview else ""
            print(
                f"  - [{issue['rule']}] ligne {line_display}: "
                f"{issue['message']}{preview_txt}"
            )

    if issues_found:
        return 1

    print("Aucune correction nécessaire.")
    return 0


def _run_fix(args: argparse.Namespace) -> int:
    """Apply Markdown corrections in-place."""

    docs_dir: Path = args.docs_dir
    if not docs_dir.exists():
        print(f"Directory not found: {docs_dir}", file=sys.stderr)
        return 1

    updated_files: List[Path] = []
    for path in _iter_markdown_files(docs_dir):
        plugin = _build_cli_plugin()
        original = path.read_text(encoding="utf-8")
        issues, fixed = _analyze_markdown(original, plugin)
        if original == fixed:
            continue
        path.write_text(fixed, encoding="utf-8")
        updated_files.append(path)
        rel_path = _format_relative(path)
        print(f"Corrigé: {rel_path} ({len(issues)} modification(s))")

    if not updated_files:
        print("Aucune correction appliquée : les fichiers étaient déjà conformes.")
    else:
        print(f"{len(updated_files)} fichier(s) mis à jour.")
    return 0


def _build_cli_plugin() -> FrenchPlugin:
    """Instantiate a plugin configured for standalone Markdown processing."""

    plugin = FrenchPlugin()
    plugin.config = make_plugin_config(
        abbreviation=Level.fix,
        casse=Level.fix,
        diacritics=Level.fix,
        foreign=Level.fix,
        justify=False,
        enable_css_bullets=False,
        summary=False,
    )
    plugin._admonition_translations = DEFAULT_ADMONITION_TRANSLATIONS.copy()
    plugin._collected_warnings = []
    plugin._foreign_processed_pages.clear()
    plugin._foreign_pattern = None
    return plugin


def _analyze_markdown(
    text: str, plugin: FrenchPlugin
) -> tuple[List[dict[str, object]], str]:
    """Return the list of pending issues and the corrected Markdown."""

    segments = _build_segments(text, plugin)
    issues: List[dict[str, object]] = []

    for rule in plugin._markdown_orchestrator.rules:
        level = getattr(plugin.config, rule.config_attr)
        level_value = getattr(level, "value", level)
        if level_value == Level.ignore.value:
            continue

        current_text = _segments_to_text(segments)
        offset = 0
        for segment in segments:
            segment_length = len(segment.text)
            if not segment.ignored:
                findings = rule.detect(segment.text)
                for start, _end, message, preview in findings:
                    absolute_start = offset + start
                    issues.append(
                        {
                            "rule": rule.name,
                            "line": plugin._line_number_for_offset(
                                current_text, absolute_start
                            ),
                            "message": message,
                            "preview": preview,
                        }
                    )
            offset += segment_length

        if level_value == Level.fix.value:
            for segment in segments:
                if segment.ignored:
                    continue
                segment.text = rule.fix(segment.text)

    current_text = _segments_to_text(segments)

    if plugin.config.foreign != Level.ignore:
        ignore_ranges = _collect_ignore_ranges(segments)
        replacements = plugin._foreign_replacements(current_text)
        applicable_replacements = [
            (start, end, phrase, replacement)
            for start, end, phrase, replacement in replacements
            if not _range_overlaps(ignore_ranges, start, end)
        ]
        for start, _end, phrase, _replacement in applicable_replacements:
            issues.append(
                {
                    "rule": "foreign",
                    "line": plugin._line_number_for_offset(current_text, start),
                    "message": f"Locution étrangère non italique : «{phrase}»",
                    "preview": phrase,
                }
            )
        if plugin.config.foreign == Level.fix:
            current_text = _apply_replacements(current_text, applicable_replacements)

    return issues, current_text


def _segments_to_text(segments: Sequence[_Segment]) -> str:
    """Concatenate segment texts preserving ignored regions."""
    return "".join(segment.text for segment in segments)


def _collect_ignore_ranges(segments: Sequence[_Segment]) -> List[Tuple[int, int]]:
    """Return absolute index ranges corresponding to ignored segments."""
    ranges: List[Tuple[int, int]] = []
    cursor = 0
    for segment in segments:
        length = len(segment.text)
        if segment.ignored:
            ranges.append((cursor, cursor + length))
        cursor += length
    return ranges


def _range_overlaps(ranges: Sequence[Tuple[int, int]], start: int, end: int) -> bool:
    """Return whether the provided span overlaps any ignored range."""
    return any(start < rng_end and end > rng_start for rng_start, rng_end in ranges)


def _build_segments(text: str, plugin: FrenchPlugin) -> List[_Segment]:
    """Split text into ignored and active segments based on directives."""
    ranges = _compute_ignore_ranges(text, plugin)
    if not ranges:
        return [_Segment(text=text, ignored=False)]

    segments: List[_Segment] = []
    cursor = 0
    for start, end in ranges:
        if cursor < start:
            segments.append(_Segment(text=text[cursor:start], ignored=False))
        segments.append(_Segment(text=text[start:end], ignored=True))
        cursor = end
    if cursor < len(text):
        segments.append(_Segment(text=text[cursor:], ignored=False))
    return segments


def _compute_ignore_ranges(text: str, plugin: FrenchPlugin) -> List[Tuple[int, int]]:
    """Combine plugin-defined ignore ranges with comment directives."""
    ranges = list(plugin._markdown_ignore_ranges(text))
    ranges.extend(_comment_ignore_ranges(text))
    return _merge_ranges(ranges)


def _merge_ranges(ranges: Sequence[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Merge overlapping or adjacent ranges."""
    if not ranges:
        return []
    sorted_ranges = sorted(ranges)
    merged: List[Tuple[int, int]] = [sorted_ranges[0]]
    for start, end in sorted_ranges[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _comment_ignore_ranges(text: str) -> List[Tuple[int, int]]:
    """Return ranges delimited by HTML comment ignore directives."""
    ranges: List[Tuple[int, int]] = []
    stack: List[Tuple[int, int]] = []

    for match in _COMMENT_DIRECTIVE_RE.finditer(text):
        closing = match.group("closing")
        variant = (match.group("variant") or "").lower()

        is_start = not closing and variant != "end"
        is_end = bool(closing) or variant == "end"

        if is_start:
            stack.append((match.start(), match.end()))
            continue

        if is_end and stack:
            _start_comment_start, start_comment_end = stack.pop()
            ranges.append((start_comment_end, match.start()))

    return [rng for rng in ranges if rng[0] < rng[1]]


def _apply_replacements(
    text: str, replacements: Sequence[tuple[int, int, str, str]]
) -> str:
    """Apply ordered replacements to the provided string."""

    if not replacements:
        return text

    pieces: List[str] = []
    last_idx = 0
    for start, end, _phrase, replacement in replacements:
        pieces.append(text[last_idx:start])
        pieces.append(replacement)
        last_idx = end
    pieces.append(text[last_idx:])
    return "".join(pieces)


def _iter_markdown_files(docs_dir: Path) -> Sequence[Path]:
    """Return Markdown files contained within ``docs_dir`` sorted by path."""
    return sorted(
        path
        for path in docs_dir.rglob("*.md")
        if path.is_file()
    )


def _format_relative(path: Path) -> str:
    """Return a path relative to the current working directory when possible."""
    root = Path.cwd().resolve()
    abs_path = path.resolve()
    try:
        return str(abs_path.relative_to(root))
    except ValueError:
        return str(abs_path)
