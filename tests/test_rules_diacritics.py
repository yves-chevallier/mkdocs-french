from __future__ import annotations

from mkdocs_french.rules import diacritics


class DummyDictionary:
    def accentize(self, word: str) -> str:
        mapping = {"ECOLE": "ÉCOLE", "Ecole": "École"}
        return mapping.get(word, word)


def test_diacritics_fix_only_uppercase(monkeypatch):
    monkeypatch.setattr(diacritics, "get_dictionary", lambda: DummyDictionary())
    text = "ECOLE Ecole"

    fixed = diacritics.fix_diacritics(text)
    assert fixed == "ÉCOLE Ecole"


def test_diacritics_detector_skips_capitalized(monkeypatch):
    monkeypatch.setattr(diacritics, "get_dictionary", lambda: DummyDictionary())
    text = "ECOLE Ecole"

    results = diacritics.det_diacritics(text)
    assert len(results) == 1
    assert results[0][2] == "Diacritique manquant : «ECOLE» → «ÉCOLE»"
