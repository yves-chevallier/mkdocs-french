from __future__ import annotations

from mkdocs_french.rules import diacritics as diacritics_module
from mkdocs_french.rules.diacritics import DiacriticsRule


rule = DiacriticsRule()


class DummyDictionary:
    def accentize(self, word: str) -> str:
        mapping = {"ECOLE": "ÉCOLE", "Ecole": "École"}
        return mapping.get(word, word)


def test_diacritics_fix_only_uppercase(monkeypatch):
    monkeypatch.setattr(diacritics_module, "get_dictionary", lambda: DummyDictionary())
    text = "ECOLE Ecole"

    fixed = rule.fix(text)
    assert fixed == "ÉCOLE Ecole"


def test_diacritics_detector_skips_capitalized(monkeypatch):
    monkeypatch.setattr(diacritics_module, "get_dictionary", lambda: DummyDictionary())
    text = "ECOLE Ecole"

    results = rule.detect(text)
    assert len(results) == 1
    assert results[0][2] == "Diacritique manquant : «ECOLE» → «ÉCOLE»"
