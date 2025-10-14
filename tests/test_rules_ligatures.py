from __future__ import annotations

from mkdocs_french.rules import ligatures as ligatures_module
from mkdocs_french.rules.ligatures import LigaturesRule


rule = LigaturesRule()


class DummyDictionary:
    def ligaturize(self, word: str) -> str:
        return {"oeuvre": "œuvre", "Oeuvre": "Œuvre"}.get(word, word)


def test_ligatures_detector_reports_missing(monkeypatch):
    monkeypatch.setattr(ligatures_module, "get_dictionary", lambda: DummyDictionary())
    results = rule.detect("Une oeuvre importante")
    assert results[0][2] == "Ligature : «oeuvre» → «œuvre»"


def test_ligatures_fix_replaces(monkeypatch):
    monkeypatch.setattr(ligatures_module, "get_dictionary", lambda: DummyDictionary())
    fixed = rule.fix("Oeuvre et oeuvre")
    assert fixed == "Œuvre et œuvre"
