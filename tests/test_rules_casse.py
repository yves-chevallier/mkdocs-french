from __future__ import annotations

import pytest

from mkdocs_french.rules.casse import CasseRule


rule = CasseRule()


def test_det_casse_skips_sentence_start():
    text = "Lundi, nous travaillerons. Erreur: Lundi, encore."
    results = rule.detect(text)
    assert not results


def test_det_casse_reports_incorrect_capitalization():
    text = "Nous partirons en Novembre et le Mardi suivant."
    results = rule.detect(text)
    messages = [entry[2] for entry in results]
    assert "Casse incorrecte pour «Novembre»" in messages
    assert "Casse incorrecte pour «Mardi»" in messages


def test_fix_casse_respects_sentence_start():
    text = "Erreur: Mardi, réunion."
    assert rule.fix(text) == text


def test_fix_casse_lowercases_words():
    text = "Nous partirons Mardi et Mercredi."
    assert rule.fix(text) == "Nous partirons mardi et mercredi."


def test_fix_casse_after_semicolon():
    text = "Erreur; Mardi, réunion."
    assert rule.fix(text) == "Erreur; mardi, réunion."


@pytest.mark.parametrize(
    "input_text,expected",
    [
        ("voyage en france et espagne", "voyage en France et Espagne"),
        ("Nous aimons la belgique.", "Nous aimons la Belgique."),
        ("États-Unis", "États-Unis"),
        ("royaume-uni", "Royaume-Uni"),
    ],
)
def test_fix_casse_uppercases_countries(input_text, expected):
    assert rule.fix(input_text) == expected


def test_det_casse_detects_countries_needing_uppercase():
    text = "la france et le royaume-uni coopèrent."
    results = rule.detect(text)
    replacements = {entry[3] for entry in results}
    assert {"France", "Royaume-Uni"} <= replacements
