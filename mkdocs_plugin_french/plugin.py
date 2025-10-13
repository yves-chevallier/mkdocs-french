# mkdocs_fr_typo/plugin.py
from __future__ import annotations

import logging
import re
import shutil
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set

from bs4 import BeautifulSoup, NavigableString, Comment
from mkdocs.config import config_options as c
from mkdocs.config.base import Config
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import BasePlugin
from .constants import (
    SKIP_TAGS,
    SKIP_PARENTS,
    DEFAULT_ADMONITION_TRANSLATIONS,
    FOREIGN_LOCUTIONS,
)
from .rules import ALL_RULES, RuleDefinition

try:  # rich est optionnel pour conserver la compatibilité sans dépendance installée
    from rich.console import Console
    from rich.table import Table
    from rich import box
except ImportError:  # pragma: no cover - environnement sans rich
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

# ---------- Config moderne par classe ----------


class Level(str, Enum):
    ignore = "ignore"
    warn = "warn"
    fix = "fix"


class FrenchPluginConfig(Config):
    # règles et leurs niveaux
    abbreviation = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.fix)
    ordinaux = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.fix)
    ligatures = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.ignore)
    casse = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.warn)
    spacing = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.fix)
    quotes = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.fix)
    units = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.fix)
    diacritics = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.warn)
    foreign = c.Choice((Level.ignore, Level.warn, Level.fix), default=Level.fix)

    # options diverses
    justify = c.Type(bool, default=True)  # injecte CSS pour texte justifié et césures
    enable_css_bullets = c.Type(bool, default=True)  # injecte CSS pour puces “–”
    css_scope_selector = c.Type(str, default="body")  # conservé pour compatibilité
    admonitions = c.Choice((Level.ignore, Level.fix), default=Level.fix)
    admonition_translations = c.Type(dict, default={})
    summary = c.Type(bool, default=False)

    # activer le marquage de lignes pour warn (auto si au moins une règle == warn)
    force_line_markers = c.Type(bool, default=False)


# ---------- Plugin ----------


class FrenchPlugin(BasePlugin[FrenchPluginConfig]):
    def __init__(self):
        super().__init__()
        self._collected_warnings: List[dict] = []
        self._temp_css_created: Set[Path] = set()
        self._extra_css: Set[Path] = set()
        self._admonition_translations: dict = {}
        self._site_dir: Optional[Path] = None

    def on_config(self, config, **kwargs):
        translations = DEFAULT_ADMONITION_TRANSLATIONS.copy()
        for key, value in self.config.admonition_translations.items():
            if value is not None:
                translations[key.lower()] = value
        self._admonition_translations = translations

        package_dir = Path(__file__).parent
        if self.config.enable_css_bullets:
            self._extra_css.add(package_dir / "css" / "french-bullet.css")
        if self.config.justify:
            self._extra_css.add(package_dir / "css" / "french-justify.css")

        self._site_dir = Path(config.site_dir)
        for entry in self._extra_css:
            config["extra_css"].append("css/" + Path(entry).name)

        return config

    def _apply_rule(
        self,
        rule: RuleDefinition,
        level: Level,
        text: str,
        src_path: str,
        cur_line: Optional[int],
    ) -> str:
        if level == Level.ignore:
            return text
        if level == Level.warn:
            for _s, _e, msg, prev in rule.detector(text):
                line_info = f"{src_path}:{cur_line}" if cur_line else src_path
                prev_txt = f" → «{prev}»" if prev else ""
                log.warning(
                    "[fr-typo:%s] %s: %s%s", rule.name, line_info, msg, prev_txt
                )
                if self.config.summary:
                    self._collected_warnings.append(
                        {
                            "rule": rule.name,
                            "file": src_path,
                            "line": cur_line,
                            "message": msg,
                            "preview": prev,
                        }
                    )
            return text
        # fix
        return rule.fixer(text)

    def on_page_content(self, html, page, config, files):
        """Traite le HTML généré d'une page."""
        soup = BeautifulSoup(html, "html.parser")

        # 1) Préparer : repérer tous les commentaires de type FRL (déjà présent)
        comments = list(soup.find_all(string=lambda t: isinstance(t, Comment)))

        # 2) Marquer les noeuds qui sont dans un block ignore
        #    On parcourt les commentaires et on localise les start/end, en collectant
        #    les noeuds entre eux, puis on ajoute leurs descendants à un set `nodes_to_skip`.
        nodes_to_skip = set()

        def _mark_ignore(node):
            if node is None:
                return
            nodes_to_skip.add(node)
            if hasattr(node, "descendants"):
                for desc in node.descendants:
                    nodes_to_skip.add(desc)

        # map comment node -> position in document order (approx)
        pos_map = {c: i for i, c in enumerate(comments)}

        # find inline and block ignores
        for comment in comments:
            txt = str(comment).strip()
            if txt.lower() == "fr-typo-ignore-start":
                # find the matching end comment
                # search subsequent comments for fr-typo-ignore-end
                for c2 in comments[pos_map[comment] + 1 :]:
                    if str(c2).strip().lower() == "fr-typo-ignore-end":
                        # collect everything between comment and c2 (inclusive of nodes between them)
                        # use .next_siblings from comment up to c2
                        node = comment.next_sibling
                        while node and node is not c2:
                            _mark_ignore(node)
                            node = node.next_sibling
                        break
            elif txt.lower() == "fr-typo-ignore":
                # inline single ignore: next_sibling expected to be the text node or element to protect,
                # or there could be a sibling comment </fr-typo-ignore> later.
                # Simple heuristic: protect the next text node
                nxt = comment.next_sibling
                while isinstance(nxt, NavigableString) and not nxt.strip():
                    nxt = nxt.next_sibling
                if nxt is not None:
                    _mark_ignore(nxt)

        # 3) Also protect elements with class/data attribute
        for el in soup.select(".fr-typo-ignore, [data-fr-typo='ignore']"):
            _mark_ignore(el)

        # Allow code/span with explicit opt-out classes or attributes
        for el in soup.select(
            "code.nohighlight, code.fr-typo-ignore, code[data-fr-typo='ignore']"
        ):
            _mark_ignore(el)
        for el in soup.select(
            "span.nohighlight, span.fr-typo-ignore, span[data-fr-typo='ignore']"
        ):
            _mark_ignore(el)

        # 4) Then, in the main iteration where you process NavigableString nodes, skip if node in nodes_to_skip

        # on parcourt en profondeur
        for node in soup.descendants:
            if isinstance(node, Comment):
                continue

            if isinstance(node, NavigableString):
                parent = node.parent
                if node in nodes_to_skip or parent in nodes_to_skip:
                    continue
                if (
                    not parent
                    or parent.name in SKIP_TAGS
                    or parent.name in SKIP_PARENTS
                ):
                    continue
                if any(getattr(p, "name", None) in SKIP_TAGS for p in parent.parents):
                    continue

                s = str(node)
                if not s.strip():
                    continue

                cfg = self.config
                src_path = getattr(
                    page.file,
                    "src_path",
                    page.file.abs_src_path if page and page.file else "<page>",
                )

                for rule in ALL_RULES:
                    level = getattr(cfg, rule.config_attr)
                    s = self._apply_rule(rule, level, s, src_path, None)

                handled_foreign = False
                if cfg.foreign != Level.ignore and parent:
                    s_text = s if s != node else str(node)
                    parents_chain = [parent]
                    if hasattr(parent, "parents"):
                        parents_chain.extend(parent.parents)
                    italic_context = any(
                        getattr(p, "name", None) in {"em", "i"} for p in parents_chain
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

    def on_page_markdown(self, markdown, page, config, files):
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
        site_dir = Path(config.site_dir)
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
        parent,
        src_path: str,
        italic_context: bool,
    ) -> tuple[bool, str]:
        if not FOREIGN_LOCUTIONS:
            return False, text

        pattern = getattr(self, "_foreign_pattern", None)
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
        new_nodes: List = []
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
                entry["rule"],
                entry["file"],
                line,
                entry["message"],
                suggestion,
            )

        console = Console()
        console.print(table)

    def _print_plain_summary(self):
        # fallback texte simple si rich n'est pas disponible
        header = "Résumé des avertissements typographiques"
        print("\n" + header)
        print("-" * len(header))
        for entry in self._collected_warnings:
            line = f"Ligne {entry['line']}" if entry["line"] else "Ligne —"
            suggestion = (
                f" | Suggestion: «{entry['preview']}»" if entry["preview"] else ""
            )
            print(
                f"[{entry['rule']}] {entry['file']} ({line}) -> {entry['message']}{suggestion}"
            )
        print()
