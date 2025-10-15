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
from .rules import Rule, RuleOrchestrator, RuleWarning, build_rules


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
    admonition_translations = c.Type(dict[str, str | None], default={})
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
        self._orchestrator = RuleOrchestrator(build_rules())
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

        config_mapping = cast(MutableMapping[str, Any], config)
        site_dir_attr = config.site_dir if hasattr(config, "site_dir") else None
        if isinstance(site_dir_attr, str):
            site_dir_value = site_dir_attr
        else:
            site_dir_raw = config_mapping.get("site_dir", "site")
            site_dir_value = str(site_dir_raw)
        site_dir = Path(site_dir_value)
        extra_css_source: Iterable[str] = config_mapping.get("extra_css", [])
        extra_css: list[str] = []
        for entry in extra_css_source:
            extra_css.append(str(entry))
        config_mapping["extra_css"] = extra_css_source

        self._site_dir = site_dir
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
    ) -> None:
        """Log warnings and optionally store them for later summary output.

        Args:
            warnings: Collection of warnings to emit.
            src_path: Source path associated with the processed content.
            cur_line: Optional line number providing additional context.
        """
        if not warnings:
            return
        line_info = f"{src_path}:{cur_line}" if cur_line else src_path

        for warning in warnings:
            prev_txt = f" → «{warning.preview}»" if warning.preview else ""
            log.warning(
                "[fr-typo:%s] %s: %s%s",
                warning.rule.name,
                line_info,
                warning.message,
                prev_txt,
            )
            if self.config.summary:
                warning_entry: WarningEntry = {
                    "rule": warning.rule.name,
                    "file": src_path,
                    "line": cur_line,
                    "message": warning.message,
                    "preview": warning.preview,
                }
                self._collected_warnings.append(warning_entry)

    def on_page_content(
        self,
        html: str,
        /,
        *,
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
                file_obj = page.file if hasattr(page, "file") else None
                if file_obj is None:
                    src_path = "<page>"
                else:
                    file_data = cast(Any, file_obj)
                    raw_src: str | None
                    if hasattr(file_data, "src_path"):
                        raw_src = cast(str | None, file_data.src_path)
                    else:
                        raw_src = None
                    if raw_src is None and hasattr(file_data, "abs_src_path"):
                        raw_src = cast(str | None, file_data.abs_src_path)
                    if raw_src is None:
                        src_path = "<page>"
                    else:
                        src_path = str(raw_src)

                s, warnings = self._orchestrator.process(
                    s,
                    self._level_for_rule,
                )
                self._emit_warnings(warnings, src_path, None)

                handled_foreign = False
                if cfg.foreign != Level.ignore and parent:
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

        return str(soup)

    def on_page_markdown(
        self,
        markdown: str,
        /,
        *,
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
        del page, config, files
        if self.config.admonitions != Level.fix:
            return markdown

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

    def on_post_build(self, *, config: MkDocsConfig) -> None:
        """Copy injected CSS files and optionally print a summary after build.

        Args:
            config: MkDocs configuration object.
        """
        config_mapping = cast(MutableMapping[str, Any], config)
        site_dir_attr = config.site_dir if hasattr(config, "site_dir") else None
        if isinstance(site_dir_attr, str):
            site_dir_value = site_dir_attr
        else:
            site_dir_raw = config_mapping.get("site_dir", "site")
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

    def _log_foreign_warning(self, phrase: str, src_path: str) -> None:
        """Record a warning for a non-italicized foreign locution.

        Args:
            phrase: Foreign expression detected in the source.
            src_path: Page path used when logging the warning.
        """
        message = f"Locution étrangère non italique : «{phrase}»"
        log.warning("[fr-typo:foreign] %s: %s", src_path, message)
        if self.config.summary:
            self._collected_warnings.append(
                {
                    "rule": "foreign",
                    "file": src_path,
                    "line": None,
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
        table.add_column("Fichier", style="green")
        table.add_column("Ligne", justify="right", style="yellow")
        table.add_column("Message", style="white")
        table.add_column("Suggestion", style="dim")

        for entry in self._collected_warnings:
            line = str(entry["line"]) if entry["line"] else "—"
            suggestion = f"«{entry['preview']}»" if entry["preview"] else ""
            table.add_row(
                entry["rule"], entry["file"], line, entry["message"], suggestion
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
            line = f"Ligne {entry['line']}" if entry["line"] else "Ligne —"
            suggestion = (
                f" | Suggestion: «{entry['preview']}»" if entry["preview"] else ""
            )
            print(
                f"[{entry['rule']}] {entry['file']} "
                f"({line}) -> {entry['message']}{suggestion}"
            )
        print()
