# mkdocs_fr_typo/plugin.py
from __future__ import annotations

import logging
import re
import shutil
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable, Tuple, List, Optional

from bs4 import BeautifulSoup, NavigableString, Comment
from mkdocs.config import config_options as c
from mkdocs.config.base import Config
from mkdocs.plugins import BasePlugin
try:  # rich est optionnel pour conserver la compatibilité sans dépendance installée
    from rich.console import Console
    from rich.table import Table
    from rich import box
except ImportError:  # pragma: no cover - environnement sans rich
    Console = None
    Table = None
    box = None

log = logging.getLogger("mkdocs.plugins.fr_typo")

NBSP = "\u00a0"  # insécable
NNBSP = "\u202f"  # fine insécable
ELLIPSIS = "\u2026"

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

    # options diverses
    enable_css_bullets = c.Type(bool, default=True)  # injecte CSS pour puces “–”
    css_scope_selector = c.Type(
        str, default="body"
    )  # pour cibler l’injection marker ::marker
    summary = c.Type(bool, default=False)

    # activer le marquage de lignes pour warn (auto si au moins une règle == warn)
    force_line_markers = c.Type(bool, default=False)


# ---------- Règles (détection / correction) ----------

"""
Chaque règle est un tuple (name, level_attr, detector, fixer).
- detector(text) -> list[(span_start, span_end, message, replacement_preview)]
- fixer(text)    -> text_corrige
Si level=warn: on appelle detector et on log.
Si level=fix : on corrige (idempotent) puis on peut re-détecter pour log optionnel.
"""

RuleResult = Tuple[int, int, str, Optional[str]]


def _regex_finditer(
    text: str,
    pattern: re.Pattern,
    make_msg: Callable[[re.Match], str],
    replacement_preview: Callable[[re.Match], Optional[str]] | None = None,
) -> List[RuleResult]:
    out: List[RuleResult] = []
    for m in pattern.finditer(text):
        prev = replacement_preview(m) if replacement_preview else None
        out.append((m.start(), m.end(), make_msg(m), prev))
    return out


def _apply_sub(
    text: str, pattern: re.Pattern, repl: str | Callable[[re.Match], str]
) -> str:
    return pattern.sub(repl, text)


# --- Abbreviations
_ABBR_BAD = re.compile(r"\b(c\s*[-\.]?\s*a\s*[-\.]?\s*d)\b", re.I)
_ABBR_PEX = re.compile(r"\b(p\s*\.?\s*ex)\b\.?", re.I)
_ABBR_NB = re.compile(r"\b(n\s*\.?\s*b)\b\.?", re.I)
_ETC_BAD = re.compile(r"\betc\s*(?:\.\.|…)\b", re.I)


def det_abbreviation(s: str) -> List[RuleResult]:
    results: List[RuleResult] = []
    results += _regex_finditer(
        s,
        _ABBR_BAD,
        lambda m: f"Abréviation mauvaise : «{m.group(0)}» ; attendu «c.-à-d.»",
        lambda m: "c.-à-d.",
    )
    results += _regex_finditer(
        s,
        _ABBR_PEX,
        lambda m: f"Abréviation : «{m.group(0)}» ; attendu «p. ex.»",
        lambda m: "p. ex.",
    )
    results += _regex_finditer(
        s,
        _ABBR_NB,
        lambda m: f"Abréviation : «{m.group(0)}» ; attendu «N. B.»",
        lambda m: "N. B.",
    )
    results += _regex_finditer(
        s, _ETC_BAD, lambda m: "«etc..» ou «etc…» → «etc.»", lambda m: "etc."
    )
    return results


def fix_abbreviation(s: str) -> str:
    s = _ABBR_BAD.sub("c.-à-d.", s)
    s = _ABBR_PEX.sub("p. ex.", s)
    s = _ABBR_NB.sub("N. B.", s)
    s = _ETC_BAD.sub("etc.", s)
    return s


# --- Ordinaux
_ORD_1ER = re.compile(r"\b1(?:\^?er)\b", re.I)
_ORD_1RE = re.compile(r"\b1(?:\^?re|ère)\b", re.I)
_ORD_EME = re.compile(r"\b([2-9]|[1-9]\d+)\s*(?:\^?e?me|\^?ème|\^?eme)\b", re.I)


def det_ordinaux(s: str) -> List[RuleResult]:
    out: List[RuleResult] = []
    out += _regex_finditer(
        s, _ORD_1RE, lambda m: f"Ordinal «{m.group(0)}» → «1re»", lambda m: "1re"
    )
    out += _regex_finditer(
        s,
        _ORD_1ER,
        lambda m: f"Vérifier «{m.group(0)}» (ok «1er» ; parfois «1re»).",
        lambda m: "1er",
    )
    out += _regex_finditer(
        s,
        _ORD_EME,
        lambda m: f"Ordinal «{m.group(0)}» → «{m.group(1)}e»",
        lambda m: f"{m.group(1)}e",
    )
    return out


def fix_ordinaux(s: str) -> str:
    s = _ORD_1RE.sub("1re", s)
    s = _ORD_1ER.sub("1er", s)
    s = _ORD_EME.sub(lambda m: f"{m.group(1)}e", s)
    return s


# --- Ligatures (whitelist)
LIG_DICT = {
    "coeur": "cœur",
    "soeur": "sœur",
    "boeuf": "bœuf",
    "coelacanthe": "cœlacanthe",
    "noeud": "nœud",
    "oeil": "œil",
    "oeuf": "œuf",
    "oeuvre": "œuvre",
    "oeuvrer": "œuvrer",
    "oedeme": "œdème",
    "oesophage": "œsophage",
    "oestrogène": "œstrogène",
    "oecuménique": "œcuménique",
    "oeillet": "œillet",
    # "oe": "œ",
    "foetus": "fœtus",
    "oedipe": "œdipe",
    "caecum": "cæcum",
    "tænia": "tænia",
    "vitae": "vitæ",
    "ex aequo": "ex æquo",
    "cænotype": "cænotype",
    "voeu": "vœu"
}


def det_ligatures(s: str) -> List[RuleResult]:
    results: List[RuleResult] = []
    for plain, lig in LIG_DICT.items():
        pat = re.compile(rf"\b{plain}\b", re.I)
        results += _regex_finditer(
            s,
            pat,
            lambda m, p=plain, l=lig: f"Ligature : «{m.group(0)}» → «{l}»",
            lambda m, l=lig: l,
        )
    return results


def fix_ligatures(s: str) -> str:
    for plain, lig in LIG_DICT.items():
        s = re.sub(rf"\b{plain}\b", lig, s, flags=re.I)
    return s


# --- Casse (mois, jours, langues/gentilés usuels)
MOIS = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
LANGS = [
    "français",
    "anglais",
    "espagnol",
    "allemand",
    "italien",
    "portugais",
    "néerlandais",
    "chinois",
    "japonais",
    "arabe",
    "russe",
]


def det_casse(s: str) -> List[RuleResult]:
    res: List[RuleResult] = []
    for w in MOIS + JOURS + LANGS:
        pat = re.compile(rf"\b{w.capitalize()}\b")
        res += _regex_finditer(
            s,
            pat,
            lambda m, base=w: f"Casse : «{m.group(0)}» → «{base}»",
            lambda m, base=w: base,
        )
    return res


def fix_casse(s: str) -> str:
    for w in MOIS + JOURS + LANGS:
        s = re.sub(rf"\b{w.capitalize()}\b", w, s)
    return s


# --- Spacing (espaces fines/insécables, apostrophe, ellipse)
RE_PUNCT_HIGH = re.compile(r"\s*([;!?»])")
RE_COLON = re.compile(r"\s*(:)")
RE_GUIL_OPEN = re.compile(r"«\s*")
RE_GUIL_CLOSE = re.compile(r"\s*»")
RE_ELLIPSIS = re.compile(r"\.\.\.")


def det_spacing(s: str) -> List[RuleResult]:
    out: List[RuleResult] = []
    # manque de fine/insécable avant ponctuation haute
    for m in re.finditer(r"(?<!\u00A0|\u202F)([:;!?»])", s):
        char = m.group(1)
        exp = "fine" if char in ";!?»" else "insécable"
        out.append((m.start(), m.end(), f"Espace {exp} manquante avant «{char}»", None))
    # guillemets sans fines
    if re.search(r"«(?!\u202F)", s):
        out.append((0, 0, "Espace fine après « manquante", None))
    if re.search(r"(?<!\u202F)»", s):
        out.append((0, 0, "Espace fine avant » manquante", None))
    # ellipse "..."
    for m in RE_ELLIPSIS.finditer(s):
        out.append(
            (m.start(), m.end(), "Ellipse ASCII «...», utiliser … (U+2026)", "…")
        )
    return out


def fix_spacing(s: str) -> str:
    # apostrophe courbe simple (élisions)
    s = re.sub(r"(?<=\w)'(?=\w)", "’", s)
    # ellipse
    s = RE_ELLIPSIS.sub(ELLIPSIS, s)
    # espaces avant ponctuation
    s = RE_PUNCT_HIGH.sub(lambda m: NNBSP + m.group(1), s)
    s = RE_COLON.sub(NBSP + ":", s)
    s = RE_GUIL_OPEN.sub("«" + NNBSP, s)
    s = RE_GUIL_CLOSE.sub(NNBSP + "»", s)
    return s


# --- Guillemets (remplacer "..." par « … » — à utiliser prudemment)
RE_ASCII_QUOTES = re.compile(r'"([^"\n]+)"')


def det_quotes(s: str) -> List[RuleResult]:
    return _regex_finditer(
        s,
        RE_ASCII_QUOTES,
        lambda m: f'Guillemets anglais → français « … » : "{m.group(1)}"',
        lambda m: f"«{NNBSP}{m.group(1)}{NNBSP}»",
    )


def fix_quotes(s: str) -> str:
    return RE_ASCII_QUOTES.sub(r"«" + NNBSP + r"\1" + NNBSP + "»", s)


# --- Unités
RE_NUM_KG = re.compile(r"(\d)\s*kg\b", re.I)
RE_NUM_PCT = re.compile(r"(\d)\s*%")
RE_NUM_EURO = re.compile(r"(\d)\s*€")
RE_CELSIUS = re.compile(r"(\d)\s*°\s*C", re.I)
RE_TIME = re.compile(r"(\d)\s*h\s*(\d{2})\b")


def det_units(s: str) -> List[RuleResult]:
    res: List[RuleResult] = []
    res += _regex_finditer(
        s,
        RE_NUM_KG,
        lambda m: "Unités : «10kg» → «10 kg»",
        lambda m: f"{m.group(1)} kg",
    )
    res += _regex_finditer(
        s, RE_NUM_PCT, lambda m: "Unités : «10%» → «10 %»", lambda m: f"{m.group(1)} %"
    )
    res += _regex_finditer(
        s, RE_NUM_EURO, lambda m: "Unités : «10€» → «10 €»", lambda m: f"{m.group(1)} €"
    )
    res += _regex_finditer(
        s,
        RE_CELSIUS,
        lambda m: "Unités : «10°C» → «10 °C»",
        lambda m: f"{m.group(1)} °C",
    )
    res += _regex_finditer(
        s,
        RE_TIME,
        lambda m: "Heure : «14h30» → «14 h 30»",
        lambda m: f"{m.group(1)} h {m.group(2)}",
    )
    return res


def fix_units(s: str) -> str:
    s = RE_NUM_KG.sub(r"\1 kg", s)
    s = RE_NUM_PCT.sub(r"\1 %", s)
    s = RE_NUM_EURO.sub(r"\1 €", s)
    s = RE_CELSIUS.sub(r"\1 °C", s)
    s = RE_TIME.sub(r"\1 h \2", s)
    return s


# ---------- Utilitaires HTML ----------

SKIP_TAGS = {"code", "pre", "kbd", "samp", "var", "script", "style", "math"}
SKIP_PARENTS = {"a", "time", "data"}


def iter_text_nodes(soup: BeautifulSoup) -> Iterable[NavigableString]:
    for el in soup.descendants:
        if isinstance(el, NavigableString) and not isinstance(el, Comment):
            parent = el.parent
            if parent and (parent.name in SKIP_TAGS or parent.name in SKIP_PARENTS):
                continue
            # skip if inside any SKIP_TAGS ancestor
            if any(
                getattr(p, "name", None) in SKIP_TAGS
                for p in parent.parents
                if hasattr(parent, "parents")
            ):
                continue
            yield el


# ---------- Plugin ----------


class FrenchPlugin(BasePlugin[FrenchPluginConfig]):
    def on_config(self, config, **kwargs):
        self._collected_warnings: List[dict] = []
        self._css_temp_created = False
        if self.config.enable_css_bullets:
            self._ensure_css_in_docs(config)
        return config

    # Marquage des lignes si nécessaire pour WARN précis
    _LINE_MARK = re.compile(r"<!--FRL:(\d+)-->")

    def _any_warn_enabled(self) -> bool:
        cfg = self.config
        return (
            any(
                getattr(cfg, name) == Level.warn
                for name in (
                    "abbreviation",
                    "ordinaux",
                    "ligatures",
                    "casse",
                    "spacing",
                    "quotes",
                    "units",
                )
            )
            or cfg.force_line_markers
        )

    def on_page_markdown(self, markdown, page, config, files):
        if not self._any_warn_enabled():
            return markdown

        # insère un commentaire HTML par ligne pour pouvoir logger la ligne correspondante
        lines = markdown.splitlines(keepends=True)

        table_sep_re = re.compile(
            r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$"
        )
        fence_re = re.compile(r"^\s*(```|~~~)")
        list_marker_re = re.compile(r"(?:[-+*]|\d+[.)])\s+")

        def _insert_table_marker(line_no: int, line: str) -> str:
            # conserve le suffixe de fin de ligne pour le réappliquer après insertion
            newline = ""
            if line.endswith("\r\n"):
                newline = "\r\n"
                body = line[:-2]
            elif line.endswith("\n"):
                newline = "\n"
                body = line[:-1]
            elif line.endswith("\r"):
                newline = "\r"
                body = line[:-1]
            else:
                body = line

            if "|" not in body:
                return f"<!--FRL:{line_no}-->{line}"

            stripped = body.lstrip()
            leading_ws = len(body) - len(stripped)
            if stripped.startswith("|"):
                pipe_idx = body.find("|", leading_ws)
                insert_pos = pipe_idx + 1
            else:
                pipe_idx = body.find("|")
                insert_pos = pipe_idx

            return (
                body[:insert_pos]
                + f"<!--FRL:{line_no}-->"
                + body[insert_pos:]
                + newline
            )

        def _insert_general_marker(line_no: int, line: str) -> str:
            newline = ""
            if line.endswith("\r\n"):
                newline = "\r\n"
                body = line[:-2]
            elif line.endswith("\n"):
                newline = "\n"
                body = line[:-1]
            elif line.endswith("\r"):
                newline = "\r"
                body = line[:-1]
            else:
                body = line

            if not body:
                return f"<!--FRL:{line_no}-->{line}"

            pos = 0
            # indent
            while pos < len(body) and body[pos] in (" ", "\t"):
                pos += 1

            # blockquote prefixes (">", possibly multiples)
            bq_pos = pos
            while bq_pos < len(body) and body[bq_pos] == ">":
                bq_pos += 1
                if bq_pos < len(body) and body[bq_pos] == " ":
                    bq_pos += 1
                pos = bq_pos

            # list markers (unordered / ordered)
            m = list_marker_re.match(body[pos:])
            if m:
                pos += m.end()

            # headings (#)
            if pos < len(body) and body[pos] == "#":
                level = 0
                while pos + level < len(body) and body[pos + level] == "#":
                    level += 1
                pos += level
                if pos < len(body) and body[pos] == " ":
                    pos += 1

            return body[:pos] + f"<!--FRL:{line_no}-->" + body[pos:] + newline

        result: List[str] = []
        i = 0
        in_table = False
        pending_separator = False
        in_code_block = False

        while i < len(lines):
            line = lines[i]
            line_no = i + 1
            stripped = line.lstrip()

            fence_match = fence_re.match(stripped)
            if fence_match:
                in_code_block = not in_code_block
                in_table = False
                pending_separator = False

            if pending_separator:
                result.append(line)
                pending_separator = False
                in_table = True
                i += 1
                continue

            if fence_match:
                result.append(line)
                i += 1
                continue

            if in_code_block:
                result.append(line)
                i += 1
                continue

            if in_table:
                if not line.strip():
                    in_table = False
                elif in_code_block:
                    in_table = False
                elif table_sep_re.match(line):
                    result.append(line)
                    i += 1
                    continue
                elif "|" in line:
                    result.append(_insert_table_marker(line_no, line))
                    i += 1
                    continue
                else:
                    in_table = False

            if (
                not in_code_block
                and i + 1 < len(lines)
                and table_sep_re.match(lines[i + 1])
                and "|" in line
            ):
                result.append(_insert_table_marker(line_no, line))
                pending_separator = True
                i += 1
                continue

            result.append(_insert_general_marker(line_no, line))
            i += 1

        return "".join(result)

    def _apply_rule(
        self,
        name: str,
        level: Level,
        text: str,
        detector: Callable[[str], List[RuleResult]],
        fixer: Callable[[str], str],
        src_path: str,
        cur_line: Optional[int],
    ) -> str:
        if level == Level.ignore:
            return text
        if level == Level.warn:
            for _s, _e, msg, prev in detector(text):
                line_info = f"{src_path}:{cur_line}" if cur_line else src_path
                prev_txt = f" → «{prev}»" if prev else ""
                log.warning(f"[fr-typo:{name}] {line_info}: {msg}{prev_txt}")
                if self.config.summary:
                    self._collected_warnings.append(
                        {
                            "rule": name,
                            "file": src_path,
                            "line": cur_line,
                            "message": msg,
                            "preview": prev,
                        }
                    )
            return text
        # fix
        new_text = fixer(text)
        return new_text

    def on_page_content(self, html, page, config, files):
        soup = BeautifulSoup(html, "html.parser")

        # suivi de ligne via commentaires FRL
        current_line: Optional[int] = None
        comments_to_remove: List[Comment] = []

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

        # on parcourt en profondeur, en mettant à jour la ligne quand on croise un commentaire
        for node in soup.descendants:
            if isinstance(node, Comment):
                m = self._LINE_MARK.fullmatch(str(node).strip())
                if m:
                    current_line = int(m.group(1))
                    comments_to_remove.append(node)

            if isinstance(node, NavigableString) and not isinstance(node, Comment):
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

                # ordre des règles
                s = self._apply_rule(
                    "abbreviation",
                    cfg.abbreviation,
                    s,
                    det_abbreviation,
                    fix_abbreviation,
                    src_path,
                    current_line,
                )
                s = self._apply_rule(
                    "ordinaux",
                    cfg.ordinaux,
                    s,
                    det_ordinaux,
                    fix_ordinaux,
                    src_path,
                    current_line,
                )
                s = self._apply_rule(
                    "ligatures",
                    cfg.ligatures,
                    s,
                    det_ligatures,
                    fix_ligatures,
                    src_path,
                    current_line,
                )
                s = self._apply_rule(
                    "casse", cfg.casse, s, det_casse, fix_casse, src_path, current_line
                )
                s = self._apply_rule(
                    "spacing",
                    cfg.spacing,
                    s,
                    det_spacing,
                    fix_spacing,
                    src_path,
                    current_line,
                )
                s = self._apply_rule(
                    "quotes",
                    cfg.quotes,
                    s,
                    det_quotes,
                    fix_quotes,
                    src_path,
                    current_line,
                )
                s = self._apply_rule(
                    "units", cfg.units, s, det_units, fix_units, src_path, current_line
                )

                if s != node:
                    node.replace_with(NavigableString(s))

        # retirer les commentaires de ligne
        for cmt in comments_to_remove:
            cmt.extract()

        return str(soup)

    def on_post_page(self, output_content, page, config):
        return output_content

    def on_post_build(self, config):
        if self.config.enable_css_bullets:
            site_css_dir = Path(config["site_dir"]) / "css"
            self._copy_css(site_css_dir)
            if self._css_temp_created:
                self._cleanup_temp_css(Path(config["docs_dir"]) / "css" / "french.css")
        if self.config.summary and self._collected_warnings:
            self._print_summary()

    def _css_source_path(self) -> Path:
        return Path(__file__).parent / "css" / "french.css"

    def _ensure_css_in_docs(self, config):
        docs_dir = Path(config["docs_dir"])
        target_dir = docs_dir / "css"
        target_path = target_dir / "french.css"
        if not target_path.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self._css_source_path(), target_path)
            self._css_temp_created = True

    def _copy_css(self, dest_dir: Path):
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self._css_source_path(), dest_dir / "french.css")

    def _cleanup_temp_css(self, temp_path: Path):
        try:
            temp_path.unlink()
        except FileNotFoundError:
            return
        parent = temp_path.parent
        try:
            next(parent.iterdir())
        except StopIteration:
            parent.rmdir()

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
