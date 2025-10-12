# mkdocs_fr_typo/plugin.py
from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Callable, Iterable, Tuple, List, Optional

from bs4 import BeautifulSoup, NavigableString, Comment
from mkdocs.plugins import BasePlugin
from mkdocs.config.base import Config
from mkdocs.config import config_options as c

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
        # rien à modifier côté mkdocs.yml; CSS sera injecté en on_post_page
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
        lines = markdown.splitlines()
        for i in range(len(lines)):
            lines[i] = f"<!--FRL:{i + 1}-->\n{lines[i]}"
        return "\n".join(lines)

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
                            # collect text nodes under this node
                            for desc in (node.descendants if hasattr(node, 'descendants') else []):
                                nodes_to_skip.add(desc)
                            nodes_to_skip.add(node)
                            node = node.next_sibling
                        break
            elif txt.lower() == "fr-typo-ignore":
                # inline single ignore: next_sibling expected to be the text node or element to protect,
                # or there could be a sibling comment </fr-typo-ignore> later.
                # Simple heuristic: protect the next text node
                nxt = c.next_sibling
                if nxt is not None:
                    nodes_to_skip.add(nxt)

        # 3) Also protect elements with class/data attribute
        for el in soup.find_all(attrs={"class": lambda v: v and "fr-typo-ignore" in v.split(),
                                    "data-fr-typo": lambda v: v == "ignore"}):
            for desc in el.descendants:
                nodes_to_skip.add(desc)

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

        # Injection CSS (puces en “–”) si demandé
        if self.config.enable_css_bullets:
            css = self._bullet_css(self.config.css_scope_selector)
            # injecter <style> avant </head> si possible
            html_str = str(soup)
            head_close = "</head>"
            if head_close in html_str:
                html_str = html_str.replace(
                    head_close,
                    f"<style id='fr-typo-bullets'>\n{css}\n</style>\n{head_close}",
                )
                return html_str
            else:
                # sinon, ajouter en tout début (fallback)
                return f"<style id='fr-typo-bullets'>\n{css}\n</style>\n" + html_str

        return str(soup)

    @staticmethod
    def _bullet_css(scope_selector: str) -> str:
        # Variante ::marker (simple) + fallback “pseudo-bullet” si ::marker est limité par le thème
        return f"""
{scope_selector} ul {{ list-style: none; padding-left: 1.25em; }}
{scope_selector} ul > li {{ position: relative; }}
{scope_selector} ul > li::before {{
  content: "–";  /* demi-cadratin */
  position: absolute;
  left: -1.25em;
}}
/* Si le thème gère bien ::marker, dé-commente pour l'utiliser plutôt que ::before :
{scope_selector} ul {{ list-style: none; }}
{scope_selector} ul > li::marker {{ content: "– "; }}
*/
        """.strip()

    def on_post_page(self, output_content, page, config):
        # Rien de spécial ici (on a injecté le CSS en on_page_content)
        return output_content
