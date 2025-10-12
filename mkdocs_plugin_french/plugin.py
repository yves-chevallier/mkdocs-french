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
from mkdocs.plugins import BasePlugin
from .constants import SKIP_TAGS, SKIP_PARENTS, DEFAULT_ADMONITION_TRANSLATIONS
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
    r'''^(?P<indent>\s*)(?P<marker>!!!|\?\?\?\+?)\s+'''
    r'''(?P<type>[A-Za-z0-9_-]+)'''
    r'''(?P<options>(?:\s+(?!")[^\s]+)*)'''
    r'''(?:\s+"(?P<title>[^"]*)")?\s*$'''
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

    # options diverses
    enable_css_bullets = c.Type(bool, default=True)  # injecte CSS pour puces “–”
    css_scope_selector = c.Type(str, default="body")  # conservé pour compatibilité
    admonitions = c.Choice((Level.ignore, Level.fix), default=Level.fix)
    admonition_translations = c.Type(dict, default={})
    summary = c.Type(bool, default=False)

    # activer le marquage de lignes pour warn (auto si au moins une règle == warn)
    force_line_markers = c.Type(bool, default=False)


# ---------- Plugin ----------


class FrenchPlugin(BasePlugin[FrenchPluginConfig]):
    def on_config(self, config, **kwargs):
        self._collected_warnings: List[dict] = []
        self._temp_css_created: Set[Path] = set()
        translations = DEFAULT_ADMONITION_TRANSLATIONS.copy()
        for key, value in self.config.admonition_translations.items():
            if value is not None:
                translations[key.lower()] = value
        self._admonition_translations = translations
        if self.config.enable_css_bullets:
            self._ensure_css_in_docs(config, ["french-bullet.css"])
            self._ensure_extra_css(config, ["css/french-bullet.css"])
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
                log.warning(f"[fr-typo:{rule.name}] {line_info}: {msg}{prev_txt}")
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
        soup = BeautifulSoup(html, "html.parser")

        IGNORE_START = re.compile(r'FR-IGNORE-START', re.I)
        IGNORE_END   = re.compile(r'FR-IGNORE-END', re.I)
        INLINE_IGNORE = re.compile(r'FR-IGNORE', re.I)  # pour <!--fr-typo-ignore--> single

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
        for c in comments:
            txt = str(c).strip()
            if txt.lower() == "fr-typo-ignore-start":
                # find the matching end comment
                # search subsequent comments for fr-typo-ignore-end
                for c2 in comments[pos_map[c]+1:]:
                    if str(c2).strip().lower() == "fr-typo-ignore-end":
                        # collect everything between c and c2 (inclusive of nodes between them)
                        # use .next_siblings from c up to c2
                        node = c.next_sibling
                        while node and node is not c2:
                            _mark_ignore(node)
                            node = node.next_sibling
                        break
            elif txt.lower() == "fr-typo-ignore":
                # inline single ignore: next_sibling expected to be the text node or element to protect,
                # or there could be a sibling comment </fr-typo-ignore> later.
                # Simple heuristic: protect the next text node
                nxt = c.next_sibling
                while isinstance(nxt, NavigableString) and not nxt.strip():
                    nxt = nxt.next_sibling
                if nxt is not None:
                    _mark_ignore(nxt)

        # 3) Also protect elements with class/data attribute
        for el in soup.select(".fr-typo-ignore, [data-fr-typo='ignore']"):
            _mark_ignore(el)

        # Allow code/span with explicit opt-out classes or attributes
        for el in soup.select("code.nohighlight, code.fr-typo-ignore, code[data-fr-typo='ignore']"):
            _mark_ignore(el)
        for el in soup.select("span.nohighlight, span.fr-typo-ignore, span[data-fr-typo='ignore']"):
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
                f"{indent}{marker} {admonition_type}{options} \"{translation}\"{newline}"
            )

        return "".join(lines)

    def on_post_page(self, output_content, page, config):
        return output_content

    def on_post_build(self, config):
        if self.config.enable_css_bullets:
            self._copy_css_to_site(config, ["french-bullet.css"])
            self._cleanup_temp_css()
        if self.config.summary and self._collected_warnings:
            self._print_summary()

    def _asset_path(self, filename: str) -> Path:
        return Path(__file__).parent / "css" / filename

    def _ensure_css_in_docs(self, config, filenames: List[str]):
        docs_dir = Path(config["docs_dir"])
        target_dir = docs_dir / "css"
        for filename in filenames:
            target_path = target_dir / filename
            if not target_path.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self._asset_path(filename), target_path)
                self._temp_css_created.add(target_path)

    def _copy_css_to_site(self, config, filenames: List[str]):
        site_css_dir = Path(config["site_dir"]) / "css"
        site_css_dir.mkdir(parents=True, exist_ok=True)
        for filename in filenames:
            shutil.copy2(self._asset_path(filename), site_css_dir / filename)

    def _cleanup_temp_css(self):
        for temp_path in list(self._temp_css_created):
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
            parent = temp_path.parent
            try:
                next(parent.iterdir())
            except StopIteration:
                parent.rmdir()
            except FileNotFoundError:
                pass
            self._temp_css_created.discard(temp_path)

    def _ensure_extra_css(self, config, entries: List[str]):
        extra_css = config.get("extra_css")
        if extra_css is None:
            extra_css = []
            config["extra_css"] = extra_css
        for entry in entries:
            if entry not in extra_css:
                extra_css.append(entry)

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
            suggestion = f" | Suggestion: «{entry['preview']}»" if entry["preview"] else ""
            print(
                f"[{entry['rule']}] {entry['file']} ({line}) -> {entry['message']}{suggestion}"
            )
        print()
