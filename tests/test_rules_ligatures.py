from __future__ import annotations

from mkdocs_french.rules import ligatures


class DummyDictionary:
    def ligaturize(self, word: str) -> str:
        return {"oeuvre": "œuvre", "Oeuvre": "Œuvre"}.get(word, word)


def test_ligatures_detector_reports_missing(monkeypatch):
    monkeypatch.setattr(ligatures, "get_dictionary", lambda: DummyDictionary())
    results = ligatures.det_ligatures("Une oeuvre importante")
    assert results[0][2] == "Ligature : «oeuvre» → «œuvre»"


def test_ligatures_fix_replaces(monkeypatch):
    monkeypatch.setattr(ligatures, "get_dictionary", lambda: DummyDictionary())
    fixed = ligatures.fix_ligatures("Oeuvre et oeuvre")
    assert fixed == "Œuvre et œuvre"
