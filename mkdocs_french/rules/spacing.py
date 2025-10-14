from __future__ import annotations

import re

from ..constants import ELLIPSIS, NBSP, NNBSP
from .base import RuleDefinition, RuleResult, regex_finditer


RE_PUNCT_HIGH = re.compile(r"\s*([;!?»])")
RE_COLON = re.compile(r"\s*(:)")
RE_GUIL_OPEN = re.compile(r"«\s*")
RE_GUIL_CLOSE = re.compile(r"\s*»")
RE_ELLIPSIS = re.compile(r"\.\.\.")
RE_FINAL_PUNCT_DOT = re.compile(r"([!?])(\s*)\.(?=(?:\s|$|[»\"')]))")
RE_COMMA_BEFORE_ELLIPSIS = re.compile(r",\s*(\.\.\.|…)")
RE_DOUBLE_HYPHEN = re.compile(r"(?<!-)--(?!-)")


def det_spacing(text: str) -> list[RuleResult]:
    out: list[RuleResult] = []
    # Missing thin or non-breaking space before high punctuation
    for match in re.finditer(r"(?<!\u00A0|\u202F)([:;!?»])", text):
        char = match.group(1)
        exp = "fine" if char in ";!?»" else "insécable"
        out.append(
            (match.start(), match.end(), f"Espace {exp} manquante avant «{char}»", None)
        )
    # Guillemets missing thin spaces
    if re.search(r"«(?!\u202F)", text):
        out.append((0, 0, "Espace fine après « manquante", None))
    if re.search(r"(?<!\u202F)»", text):
        out.append((0, 0, "Espace fine avant » manquante", None))
    # ASCII ellipsis "..."
    out += regex_finditer(
        text,
        RE_ELLIPSIS,
        lambda _: "Ellipse ASCII «...», utiliser … (U+2026)",
        lambda _: ELLIPSIS,
    )
    out += regex_finditer(
        text,
        RE_FINAL_PUNCT_DOT,
        lambda m: f"Ponctuation finale superflue après «{m.group(1)}»",
        lambda m: f"{m.group(1)}{m.group(2)}",
    )
    out += regex_finditer(
        text,
        RE_COMMA_BEFORE_ELLIPSIS,
        lambda _: "Virgule superflue avant ellipse",
        lambda _: ELLIPSIS,
    )
    out += regex_finditer(
        text,
        RE_DOUBLE_HYPHEN,
        lambda _: "Utiliser un tiret cadratin (—) à la place de «--»",
        lambda _: "—",
    )
    return out


def fix_spacing(text: str) -> str:
    text = RE_FINAL_PUNCT_DOT.sub(lambda m: m.group(1) + m.group(2), text)
    text = RE_COMMA_BEFORE_ELLIPSIS.sub(lambda m: m.group(1), text)
    text = RE_DOUBLE_HYPHEN.sub("—", text)
    # Curly apostrophes for elisions
    text = re.sub(r"(?<=\w)'(?=\w)", "’", text)
    # Ellipsis normalization
    text = RE_ELLIPSIS.sub(ELLIPSIS, text)
    # Insert spacing before punctuation
    text = RE_PUNCT_HIGH.sub(lambda m: NNBSP + m.group(1), text)
    text = RE_COLON.sub(NBSP + ":", text)
    text = RE_GUIL_OPEN.sub("«" + NNBSP, text)
    text = RE_GUIL_CLOSE.sub(NNBSP + "»", text)
    return text


RULE = RuleDefinition(
    name="spacing", config_attr="spacing", detector=det_spacing, fixer=fix_spacing
)
