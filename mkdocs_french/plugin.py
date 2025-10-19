"""MkDocs plugin implementation enforcing French typography conventions."""

# mkdocs_fr_typo/plugin.py
# pylint: disable=invalid-name
from __future__ import annotations

from collections.abc import Iterable, MutableMapping
from enum import Enum
import logging
from pathlib import Path
import re
import shutil
from typing import Any, cast
from types import SimpleNamespace

from bs4 import BeautifulSoup, Comment
from bs4.element import NavigableString, PageElement, Tag
from mkdocs.config import config_options as c
from mkdocs.config.base import Config
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page

from .constants import (
    DEFAULT_ADMONITION_TRANSLATIONS,
    FOREIGN_LOCUTIONS,
    SKIP_PARENTS,
    SKIP_TAGS,
)
from .rules import (
    Rule,
    RuleOrchestrator,
    RuleWarning,
    build_html_rules,
    build_markdown_rules,
)


ConfigTranslationMap = MutableMapping[str, str | None]
WarningEntry = dict[str, Any]


try:  # rich is optional to keep compatibility without the dependency installed
    from rich import box
    from rich.console import Console
    from rich.table import Table
except ImportError:  # pragma: no cover - environment without rich
    Console = None
    Table = None
    box = None

log = logging.getLogger("mkdocs.plugins.fr_typo")

RE_ADMONITION = re.compile(
    r"""^(?P<indent>\s*)(?P<marker>!!!|\?\?\?\+?)\s+"""
    r"""(?P<type>[A-Za-z0-9_-]+)"""
    r"""(?P<options>(?:\s+(?!")[^\s]+)*)"""
    r"""(?:\s+"(?P<title>[^"]*)")?\s*$"""
)

# ---------- Class-based config ----------


class Level(str, Enum):  # pylint: disable=invalid-name
    """Severity levels controlling how rules behave."""

    ignore = "ignore"
    warn = "warn"
    fix = "fix"


class FrenchPluginConfig(Config):
    """Configuration schema for the French typography plugin."""

    # rule levels
    abbreviation = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.fix)
    ordinaux = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.fix)
    ligatures = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.ignore)
    casse = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.warn)
    spacing = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.fix)
    quotes = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.fix)
    units = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.fix)
    diacritics = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.warn)
    foreign = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.fix)

    # miscellaneous options
    justify = c.Type(bool, default=True)  # inject CSS for justification and hyphenation
    enable_css_bullets = c.Type(bool, default=True)  # inject CSS for dash bullets
    css_scope_selector = c.Type(str, default="body")  # kept for compatibility
    admonitions = c.Choice((Level.ignore, Level.fix), default=Level.fix)
    admonition_translations = c.Type(dict, default={})
    summary = c.Type(bool, default=False)

    # enable line markers when warn is active (auto if any rule == warn)
    force_line_markers = c.Type(bool, default=False)


# ---------- Plugin ----------


class FrenchPlugin(BasePlugin[FrenchPluginConfig]):
    """MkDocs plugin that fixes French typography and highlights issues."""

    def __init__(self):
        """Initialize runtime state and build the rule orchestrator."""
        super().__init__()
        self._collected_warnings: list[WarningEntry] = []
        self._extra_css: set[Path] = set()
        self._admonition_translations: dict[str, str] = {}
        self._site_dir: Path | None = None
        self._docs_dir: Path = Path.cwd() / "docs"
        self._markdown_orchestrator = RuleOrchestrator(build_markdown_rules())
        self._html_orchestrator = RuleOrchestrator(build_html_rules())
        self._foreign_processed_pages: set[str] = set()
        self._foreign_pattern: re.Pattern[str] | None = None

    def on_config(self, config: MkDocsConfig) -> MkDocsConfig | None:
        """Enrich the MkDocs configuration with plugin-specific assets.

        Args:
            config: MkDocs configuration object.

        Returns:
            The possibly mutated configuration object.
        """
        translations: dict[str, str] = DEFAULT_ADMONITION_TRANSLATIONS.copy()
        config_translations = cast(
            ConfigTranslationMap, self.config.admonition_translations
        )
        custom_translations: dict[str, str | None] = dict(config_translations.items())
        for key, value in custom_translations.items():
            if value is not None:
                translations[key.lower()] = value
        self._admonition_translations = translations

        package_dir = Path(__file__).parent
        if self.config.enable_css_bullets:
            self._extra_css.add(package_dir / "css" / "french-bullet.css")
        if self.config.justify:
            self._extra_css.add(package_dir / "css" / "french-justify.css")

        config_mapping: MutableMapping[str, Any] | None = (
            cast(MutableMapping[str, Any], config) if hasattr(config, "get") else None
        )
        site_dir_attr = config.site_dir if hasattr(config, "site_dir") else None
        if isinstance(site_dir_attr, str):
            site_dir_value = site_dir_attr
        else:
            site_dir_raw = (
                config_mapping.get("site_dir", "site")
                if config_mapping is not None
                else getattr(config, "site_dir", "site")
            )
            site_dir_value = str(site_dir_raw)
        site_dir = Path(site_dir_value)
        if config_mapping is not None:
            extra_css_source: Iterable[str] = config_mapping.get("extra_css", [])
        else:
            extra_css_source = getattr(config, "extra_css", [])
        extra_css: list[str] = [str(entry) for entry in extra_css_source]
        if config_mapping is not None:
            config_mapping["extra_css"] = extra_css
        if hasattr(config, "extra_css"):
            setattr(config, "extra_css", extra_css)

        self._site_dir = site_dir
        docs_dir_attr = config.docs_dir if hasattr(config, "docs_dir") else None
        if isinstance(docs_dir_attr, str):
            docs_dir_value = docs_dir_attr
        else:
            docs_dir_raw = (
                config_mapping.get("docs_dir", "docs")
                if config_mapping is not None
                else getattr(config, "docs_dir", "docs")
            )
            docs_dir_value = str(docs_dir_raw)
        docs_dir_path = Path(docs_dir_value)
        if not docs_dir_path.is_absolute():
            docs_dir_path = (Path.cwd() / docs_dir_path).resolve()
        self._docs_dir = docs_dir_path
        for entry in self._extra_css:
            css_name = "css/" + Path(entry).name
            if css_name not in extra_css:
                extra_css.append(css_name)

        return config

    def _level_for_rule(self, rule: Rule) -> Level | str:
        """Return the configured severity level for the given rule.

        Args:
            rule: Rule instance whose level should be retrieved.

        Returns:
            Configured level (enum or string) for the rule.
        """
        return getattr(self.config, rule.config_attr)

    def _emit_warnings(
        self,
        warnings: list[RuleWarning],
        src_path: str,
        cur_line: int | None,
        cur_column: int | None = None,
    ) -> None:
        """Log warnings and optionally store them for later summary output.

        Args:
            warnings: Collection of warnings to emit.
            src_path: Source path associated with the processed content.
            cur_line: Optional line number providing additional context.
        """
        if not warnings:
            return
        normalized_path = self._normalize_path(src_path)
        location = self._format_location(normalized_path, cur_line, cur_column)

        for warning in warnings:
            prev_txt = f" → «{warning.preview}»" if warning.preview else ""
            log.warning(
                "[fr-typo:%s] %s: %s%s",
                warning.rule.name,
                location,
                warning.message,
                prev_txt,
            )
            if self.config.summary:
                warning_entry: WarningEntry = {
                    "rule": warning.rule.name,
                    "file": normalized_path,
                    "line": cur_line,
                    "column": cur_column,
                    "message": warning.message,
                    "preview": warning.preview,
                }
                self._collected_warnings.append(warning_entry)

    def _source_path_for_page(self, page: Page) -> str:
        """Return the best-effort source path for the given MkDocs page."""
        file_obj = getattr(page, "file", None)
        if file_obj is None:
            return "<page>"
        file_data = cast(Any, file_obj)
        raw_src = cast(str | None, getattr(file_data, "src_path", None))
        abs_src = cast(str | None, getattr(file_data, "abs_src_path", None))
        normalized = self._normalize_path(raw_src, abs_src)
        return normalized

    @staticmethod
    def _line_number_for_offset(text: str, index: int) -> int:
        """Estimate the 1-based line number for a given string offset."""
        line, _ = FrenchPlugin._line_column_for_offset(text, index)
        return line

    @staticmethod
    def _line_column_for_offset(text: str, index: int) -> tuple[int, int]:
        """Return the 1-based line and column for a string offset."""
        line = text.count("\n", 0, index) + 1
        last_newline = text.rfind("\n", 0, index)
        if last_newline == -1:
            column = index + 1
        else:
            column = index - last_newline
        return line, column

    def _normalize_path(
        self, raw_path: str | Path | None, abs_path: str | Path | None = None
    ) -> str:
        """Return a path relative to the current working directory whenever possible."""

        if raw_path in (None, "", "<page>") and abs_path in (None, ""):
            return "<page>"

        candidates: list[Path] = []

        docs_dir = getattr(self, "_docs_dir", None)
        if raw_path and raw_path not in ("", "<page>"):
            raw_candidate = Path(str(raw_path))
            if raw_candidate.is_absolute():
                candidates.append(raw_candidate)
            else:
                if docs_dir:
                    docs_dir_path = Path(docs_dir)
                    docs_dir_name = docs_dir_path.name
                    if raw_candidate.parts and raw_candidate.parts[0] == docs_dir_name:
                        candidates.append(raw_candidate)
                    else:
                        candidates.append(docs_dir_path / raw_candidate)
                candidates.append(raw_candidate)

        if abs_path and str(abs_path):
            abs_candidate = Path(str(abs_path))
            candidates.append(abs_candidate)

        cwd = Path.cwd()
        for candidate in candidates:
            if not candidate.is_absolute():
                return str(candidate)
            candidate_resolved = candidate.resolve()
            try:
                relative = candidate_resolved.relative_to(cwd)
                return str(relative)
            except ValueError:
                continue

        if candidates:
            candidate = candidates[0]
            return str(candidate.resolve() if candidate.is_absolute() else candidate)

        return "<page>"

    def _format_location(
        self, path: str, line: int | None, column: int | None
    ) -> str:
        """Format a path with optional line and column for CLI navigation."""
        normalized = self._normalize_path(path)
        location = normalized
        if line is not None:
            location += f":{line}"
            if column is not None:
                location += f":{column}"
        return f"'{location}'"

    def on_page_content(
        self,
        html: str,
        page: Page,
        config: MkDocsConfig,
        files: Files,
    ) -> str:
        """Process the generated HTML of a page.

        Args:
            html: Rendered HTML string produced by MkDocs.
            page: MkDocs page instance currently being processed.
            config: MkDocs configuration object.
            files: MkDocs files collection (unused).

        Returns:
            Updated HTML string with typography fixes applied.
        """
        del config, files
        plugin_config: FrenchPluginConfig = self.config
        src_path = self._source_path_for_page(page)
        soup = BeautifulSoup(html, "html.parser")

        # 1) Collect FRL marker comments
        comments = list(soup.find_all(string=lambda t: isinstance(t, Comment)))

        # 2) Mark nodes contained inside ignore blocks
        #    Iterate over comment pairs, gather the nodes between them,
        #    then mark descendants.
        nodes_to_skip_ids: set[int] = set()  # object ids sidestep Tag.__hash__ hot path

        def _mark_ignore(node: PageElement | None) -> None:
            if node is None:
                return
            nodes_to_skip_ids.add(id(cast(object, node)))
            descendants = cast(Iterable[PageElement], getattr(node, "descendants", ()))
            for descendant in descendants:
                nodes_to_skip_ids.add(id(cast(object, descendant)))

        def _element_name(element: PageElement) -> str | None:
            return cast(str | None, getattr(element, "name", None))

        # Map each comment to its position in document order
        pos_map = {c: i for i, c in enumerate(comments)}

        # Find inline and block ignore directives
        for comment in comments:
            txt = str(comment).strip()
            if txt.lower() == "fr-typo-ignore-start":
                # Locate the matching end comment
                for c2 in comments[pos_map[comment] + 1 :]:
                    if str(c2).strip().lower() == "fr-typo-ignore-end":
                        # Mark every sibling between the start and end markers
                        node = comment.next_sibling
                        while node and node is not c2:
                            _mark_ignore(node)
                            node = node.next_sibling
                        break
            elif txt.lower() == "fr-typo-ignore":
                # Single inline ignore: protect the following meaningful sibling
                nxt = comment.next_sibling
                while isinstance(nxt, NavigableString) and not nxt.strip():
                    nxt = nxt.next_sibling
                if nxt is not None:
                    _mark_ignore(nxt)

        # 3) Protect nodes opt-out via class or data attribute
        for el in soup.select(".fr-typo-ignore, [data-fr-typo='ignore']"):
            _mark_ignore(el)

        # Preserve code/span elements with explicit opt-out hooks
        for el in soup.select(
            "code.nohighlight, code.fr-typo-ignore, code[data-fr-typo='ignore']"
        ):
            _mark_ignore(el)
        for el in soup.select(
            "span.nohighlight, span.fr-typo-ignore, span[data-fr-typo='ignore']"
        ):
            _mark_ignore(el)

        # 4) Skip ignored nodes during traversal

        # Depth-first traversal
        for node in soup.descendants:
            if isinstance(node, Comment):
                continue

            if isinstance(node, NavigableString):
                parent = node.parent
                if id(node) in nodes_to_skip_ids:
                    continue
                if parent and id(parent) in nodes_to_skip_ids:
                    continue
                if (
                    not parent
                    or parent.name in SKIP_TAGS
                    or parent.name in SKIP_PARENTS
                ):
                    continue
                ancestor_iter = cast(
                    Iterable[PageElement], getattr(parent, "parents", ())
                )
                if any(_element_name(p) in SKIP_TAGS for p in ancestor_iter):
                    continue

                s = str(node)
                if not s.strip():
                    continue

                cfg = plugin_config
                s, warnings = self._html_orchestrator.process(
                    s,
                    self._level_for_rule,
                )
                self._emit_warnings(warnings, src_path, None)

                handled_foreign = False
                if (
                    cfg.foreign != Level.ignore
                    and parent
                    and src_path not in self._foreign_processed_pages
                ):
                    s_text = s if s != node else str(node)
                    parents_chain: list[PageElement] = [parent]
                    parents_chain.extend(
                        cast(Iterable[PageElement], getattr(parent, "parents", ()))
                    )
                    italic_context = any(
                        _element_name(p) in {"em", "i"} for p in parents_chain
                    )
                    handled_foreign, s_text = self._apply_foreign(
                        s_text,
                        cfg.foreign,
                        soup,
                        node,
                        parent,
                        src_path,
                        italic_context,
                    )
                    if handled_foreign:
                        continue
                    s = s_text

                if s != node:
                    node.replace_with(NavigableString(s))

        if src_path != "<page>":
            self._foreign_processed_pages.discard(src_path)

        return str(soup)

    def on_page_markdown(
        self,
        markdown: str,
        page: Page,
        config: MkDocsConfig,
        files: Files,
    ) -> str:
        """Decorate admonitions in markdown before rendering.

        Args:
            markdown: Markdown source string about to be rendered.
            page: MkDocs page instance (unused).
            config: MkDocs configuration (unused).
            files: MkDocs files collection (unused).

        Returns:
            The potentially modified markdown content.
        """
        del config, files
        src_path = self._source_path_for_page(page)

        processed = self._apply_markdown_rules(markdown, src_path)

        if self.config.admonitions == Level.fix:
            processed = self._translate_admonitions(processed)

        return processed

    def on_post_build(self, config: MkDocsConfig) -> None:
        """Copy injected CSS files and optionally print a summary after build.

        Args:
            config: MkDocs configuration object.
        """
        config_mapping: MutableMapping[str, Any] | None = (
            cast(MutableMapping[str, Any], config) if hasattr(config, "get") else None
        )
        site_dir_attr = config.site_dir if hasattr(config, "site_dir") else None
        if isinstance(site_dir_attr, str):
            site_dir_value = site_dir_attr
        else:
            site_dir_raw = (
                config_mapping.get("site_dir", "site")
                if config_mapping is not None
                else getattr(config, "site_dir", "site")
            )
            site_dir_value = str(site_dir_raw)
        site_dir = Path(site_dir_value)
        css_dir = site_dir / "css"

        css_dir.mkdir(parents=True, exist_ok=True)
        for entry in self._extra_css:
            dst = css_dir / Path(entry).name
            shutil.copyfile(entry, dst)

        if self.config.summary and self._collected_warnings:
            self._print_summary()

    def _apply_foreign(
        self,
        text: str,
        level: Level,
        soup: BeautifulSoup,
        node: NavigableString,
        parent: Tag | None,
        src_path: str,
        italic_context: bool,
    ) -> tuple[bool, str]:
        """Italicize foreign locutions or emit warnings depending on the level.

        Args:
            text: Raw text node content being processed.
            level: Severity level for the foreign locution rule.
            soup: BeautifulSoup document used to create new nodes.
            node: Current text node in the DOM tree.
            parent: Parent element of the current text node.
            src_path: Source path of the page for logging purposes.
            italic_context: Whether the text already resides in an italic context.

        Returns:
            Tuple containing a flag indicating whether the node was replaced and
            the possibly modified text.
        """
        del parent
        if not FOREIGN_LOCUTIONS:
            return False, text

        pattern = self._foreign_pattern
        if pattern is None:
            escaped = "|".join(re.escape(loc) for loc in FOREIGN_LOCUTIONS)
            self._foreign_pattern = re.compile(
                rf"(?<![\w-])({escaped})(?![\w-])", re.IGNORECASE
            )
            pattern = self._foreign_pattern

        matches = list(pattern.finditer(text))
        if not matches:
            return False, text

        if level == Level.warn:
            for match in matches:
                self._log_foreign_warning(match.group(1), src_path)
            return False, text

        # Level.fix
        new_nodes: list[NavigableString | Tag] = []
        last_idx = 0
        for match in matches:
            start, end = match.span()
            if start < last_idx:
                continue
            before = text[last_idx:start]
            if before:
                new_nodes.append(NavigableString(before))
            if italic_context:
                normal_span = soup.new_tag("span")
                normal_span.attrs["style"] = "font-style: normal;"
                normal_span.string = match.group(1)
                new_nodes.append(normal_span)
            else:
                em_tag = soup.new_tag("em")
                em_tag.string = match.group(1)
                new_nodes.append(em_tag)
            last_idx = end
        tail = text[last_idx:]
        if tail:
            new_nodes.append(NavigableString(tail))

        if not new_nodes:
            return False, text

        first = new_nodes[0]
        node.replace_with(first)
        current = first
        for new_child in new_nodes[1:]:
            current.insert_after(new_child)
            current = new_child
        return True, text

    def _log_foreign_warning(
        self,
        phrase: str,
        src_path: str,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        """Record a warning for a non-italicized foreign locution.

        Args:
            phrase: Foreign expression detected in the source.
            src_path: Page path used when logging the warning.
        """
        message = f"Locution étrangère non italique : «{phrase}»"
        normalized_path = self._normalize_path(src_path)
        location = self._format_location(normalized_path, line, column)
        log.warning("[fr-typo:foreign] %s: %s", location, message)
        if self.config.summary:
            self._collected_warnings.append(
                {
                    "rule": "foreign",
                    "file": normalized_path,
                    "line": line,
                    "column": column,
                    "message": message,
                    "preview": phrase,
                }
            )

    def _print_summary(self):
        """Display a formatted summary of collected warnings."""
        if Table is None or Console is None or box is None:
            self._print_plain_summary()
            return

        table = Table(
            title="Résumé des avertissements typographiques",
            title_style="bold bright_white",
            header_style="bold magenta",
            show_lines=True,
            box=box.ROUNDED,
            border_style="grey50",
            row_styles=["grey35", ""],
            pad_edge=False,
            padding=(0, 1),
        )
        table.add_column("Règle", style="cyan", no_wrap=True)
        table.add_column("Emplacement", style="green")
        table.add_column("Message", style="white")
        table.add_column("Suggestion", style="dim")

        for entry in self._collected_warnings:
            location = self._format_location(
                entry["file"], entry.get("line"), entry.get("column")
            )
            suggestion = f"«{entry['preview']}»" if entry["preview"] else ""
            table.add_row(
                entry["rule"], location, entry["message"], suggestion
            )

        console = Console()
        console.print(table)

    def _print_plain_summary(self):
        """Fallback plain-text summary when ``rich`` is unavailable."""
        # Plain-text fallback when rich is unavailable
        header = "Résumé des avertissements typographiques"
        print("\n" + header)
        print("-" * len(header))
        for entry in self._collected_warnings:
            location = self._format_location(
                entry["file"], entry.get("line"), entry.get("column")
            )
            suggestion = (
                f" | Suggestion: «{entry['preview']}»" if entry["preview"] else ""
            )
            print(
                f"[{entry['rule']}] {location} -> {entry['message']}{suggestion}"
            )
        print()

    def _apply_markdown_rules(self, markdown: str, src_path: str) -> str:
        """Run markdown-stage rules and foreign locution handling."""
        processed, warnings = self._markdown_orchestrator.process(
            markdown, self._level_for_rule
        )
        if warnings:
            for warning in warnings:
                line, column = self._line_column_for_offset(markdown, warning.start)
                self._emit_warnings([warning], src_path, line, column)
        if processed != markdown:
            markdown = processed

        cfg = self.config
        if cfg.foreign != Level.ignore:
            markdown = self._apply_foreign_markdown(markdown, cfg.foreign, src_path)
            if src_path != "<page>":
                self._foreign_processed_pages.add(src_path)
        else:
            self._foreign_processed_pages.discard(src_path)

        return markdown

    def _translate_admonitions(self, markdown: str) -> str:
        """Translate admonition titles when no explicit title is provided."""
        lines = markdown.splitlines(keepends=True)

        def split_newline(text: str) -> tuple[str, str]:
            if text.endswith("\r\n"):
                return text[:-2], "\r\n"
            if text.endswith("\n"):
                return text[:-1], "\n"
            if text.endswith("\r"):
                return text[:-1], "\r"
            return text, ""

        for idx, raw in enumerate(lines):
            body, newline = split_newline(raw)
            match = RE_ADMONITION.match(body)
            if not match:
                continue
            admonition_type = match.group("type")
            title = match.group("title")
            translation = self._admonition_translations.get(admonition_type.lower())
            if translation is None or (title and title.strip()):
                continue

            indent = match.group("indent")
            marker = match.group("marker")
            options = match.group("options") or ""
            lines[idx] = (
                f'{indent}{marker} {admonition_type}{options} "{translation}"{newline}'
            )

        return "".join(lines)

    def _apply_foreign_markdown(
        self,
        markdown: str,
        level: Level,
        src_path: str,
    ) -> str:
        """Handle foreign locutions directly in the Markdown source."""
        if not FOREIGN_LOCUTIONS:
            return markdown

        replacements = self._foreign_replacements(markdown)
        if not replacements:
            return markdown

        if level == Level.warn:
            for start, _, phrase, _ in replacements:
                line, column = self._line_column_for_offset(markdown, start)
                self._log_foreign_warning(phrase, src_path, line, column)
            if src_path != "<page>":
                self._foreign_processed_pages.add(src_path)
            return markdown

        pieces: list[str] = []
        last_idx = 0

        for start, end, phrase, replacement in replacements:
            pieces.append(markdown[last_idx:start])
            pieces.append(replacement)
            last_idx = end

        pieces.append(markdown[last_idx:])

        if src_path != "<page>":
            self._foreign_processed_pages.add(src_path)

        return "".join(pieces)

    def _foreign_replacements(
        self, markdown: str
    ) -> list[tuple[int, int, str, str]]:
        """Compute replacements required for foreign locutions."""
        pattern = self._foreign_pattern
        if pattern is None:
            escaped = "|".join(re.escape(loc) for loc in FOREIGN_LOCUTIONS)
            self._foreign_pattern = re.compile(
                rf"(?<![\w-])({escaped})(?![\w-])", re.IGNORECASE
            )
            pattern = self._foreign_pattern

        italic_ranges = self._compute_markdown_italic_ranges(markdown)
        replacements: list[tuple[int, int, str, str]] = []
        last_idx = 0

        for match in pattern.finditer(markdown):
            start, end = match.span()
            if start < last_idx:
                continue

            if self._is_already_wrapped_foreign(markdown, start, end):
                last_idx = end
                continue

            phrase = match.group(1)
            if self._is_inside_markdown_italic(start, end, italic_ranges):
                replacement = self._wrap_foreign_span(phrase)
            else:
                replacement = self._wrap_foreign_em(phrase)

            replacements.append((start, end, phrase, replacement))
            last_idx = end

        return replacements

    @staticmethod
    def _wrap_foreign_em(text: str) -> str:
        """Return Markdown-emphasis markup for a foreign locution."""
        return f"_{text}_"

    @staticmethod
    def _wrap_foreign_span(text: str) -> str:
        """Return inline HTML span ensuring roman style inside italic context."""
        return f'<span style="font-style: normal;">{text}</span>'

    @staticmethod
    def _is_inside_markdown_italic(
        start: int, end: int, italic_ranges: list[tuple[int, int]]
    ) -> bool:
        """Return whether an index range is located within italic markup."""
        for rng_start, rng_end in italic_ranges:
            if rng_start <= start and end <= rng_end:
                return True
        return False

    @staticmethod
    def _is_already_wrapped_foreign(markdown: str, start: int, end: int) -> bool:
        """Detect whether the matched span already carries our markup."""
        span_prefix = '<span style="font-style: normal;">'
        if markdown[max(0, start - len(span_prefix)) : start].lower().endswith(
            span_prefix
        ) and markdown[end : end + len("</span>")].lower().startswith("</span>"):
            return True
        if start >= 1 and end < len(markdown):
            if markdown[start - 1] in {"_", "*"} and markdown[end] == markdown[start - 1]:
                return True
        return False

    def _compute_markdown_italic_ranges(self, markdown: str) -> list[tuple[int, int]]:
        """Return rough ranges corresponding to italic segments in Markdown."""
        ranges: list[tuple[int, int]] = []
        stack: list[tuple[str, int]] = []
        i = 0
        length = len(markdown)

        while i < length:
            if markdown.startswith("```", i) or markdown.startswith("~~~", i):
                fence = markdown[i : i + 3]
                closing = markdown.find(fence, i + 3)
                if closing == -1:
                    break
                i = closing + 3
                continue

            char = markdown[i]
            if char == "\\":
                i += 2
                continue
            if char == "`":
                end = markdown.find("`", i + 1)
                if end == -1:
                    break
                i = end + 1
                continue

            if char in "*_":
                next_char = markdown[i + 1] if i + 1 < length else ""
                if next_char == char:
                    i += 2
                    continue
                prev_char = markdown[i - 1] if i > 0 else ""
                if prev_char.isalnum() and next_char.isalnum():
                    i += 1
                    continue
                if stack and stack[-1][0] == char:
                    _, open_idx = stack.pop()
                    ranges.append((open_idx + 1, i))
                else:
                    stack.append((char, i))
                i += 1
                continue

            i += 1

        for match in re.finditer(
            r"<(em|i)\b[^>]*>(.*?)</\1>", markdown, re.IGNORECASE | re.DOTALL
        ):
            ranges.append((match.start(2), match.end(2)))

        ranges.sort()
        return ranges


def make_plugin_config(**overrides: Any) -> SimpleNamespace:
    """Create a lightweight configuration namespace for standalone usage."""

    defaults = {
        "abbreviation": Level.fix,
        "ordinaux": Level.fix,
        "ligatures": Level.ignore,
        "casse": Level.warn,
        "spacing": Level.fix,
        "quotes": Level.fix,
        "units": Level.fix,
        "diacritics": Level.warn,
        "foreign": Level.fix,
        "justify": True,
        "enable_css_bullets": True,
        "css_scope_selector": "body",
        "admonitions": Level.fix,
        "admonition_translations": {},
        "summary": False,
        "force_line_markers": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)
