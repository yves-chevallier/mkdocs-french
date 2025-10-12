from __future__ import annotations

import re
from .base import RuleDefinition, RuleResult, regex_finditer
from ..constants import NBSP, NNBSP, ELLIPSIS

RE_PUNCT_HIGH = re.compile(r"\s*([;!?»])")
RE_COLON = re.compile(r"\s*(:)")
RE_GUIL_OPEN = re.compile(r"«\s*")
RE_GUIL_CLOSE = re.compile(r"\s*»")
RE_ELLIPSIS = re.compile(r"\.\.\.")


def det_spacing(text: str) -> list[RuleResult]:
    out: list[RuleResult] = []
    # manque de fine/insécable avant ponctuation haute
    for match in re.finditer(r"(?<!\u00A0|\u202F)([:;!?»])", text):
        char = match.group(1)
        exp = "fine" if char in ";!?»" else "insécable"
        out.append(
            (match.start(), match.end(), f"Espace {exp} manquante avant «{char}»", None)
        )
    # guillemets sans fines
    if re.search(r"«(?!\u202F)", text):
        out.append((0, 0, "Espace fine après « manquante", None))
    if re.search(r"(?<!\u202F)»", text):
        out.append((0, 0, "Espace fine avant » manquante", None))
    # ellipse "..."
    out += regex_finditer(
        text,
        RE_ELLIPSIS,
        lambda _: "Ellipse ASCII «...», utiliser … (U+2026)",
        lambda _: ELLIPSIS,
    )
    return out


def fix_spacing(text: str) -> str:
    # apostrophe courbe simple (élisions)
    text = re.sub(r"(?<=\w)'(?=\w)", "’", text)
    # ellipse
    text = RE_ELLIPSIS.sub(ELLIPSIS, text)
    # espaces avant ponctuation
    text = RE_PUNCT_HIGH.sub(lambda m: NNBSP + m.group(1), text)
    text = RE_COLON.sub(NBSP + ":", text)
    text = RE_GUIL_OPEN.sub("«" + NNBSP, text)
    text = RE_GUIL_CLOSE.sub(NNBSP + "»", text)
    return text


RULE = RuleDefinition(
    name="spacing",
    config_attr="spacing",
    detector=det_spacing,
    fixer=fix_spacing,
)

