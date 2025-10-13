from __future__ import annotations

import gzip
import json

from mkdocs_french.artifacts import SCHEMA_VERSION
from mkdocs_french.dictionary import Dictionary


def make_dictionary(words: set[str]) -> Dictionary:
    dictionary = Dictionary()
    dictionary.words = set(words)
    dictionary._build_indexes()
    dictionary._prepared = True
    dictionary._prepare_attempted = True
    return dictionary


def test_ligaturize_returns_expected_form():
    dictionary = make_dictionary({"œdipe"})

    assert dictionary.ligaturize("oedipe") == "œdipe"
    assert dictionary.ligaturize("Oedipe") == "Œdipe"
    assert dictionary.ligaturize("OEDIPE") == "ŒDIPE"


def test_ligaturize_no_change_when_unknown():
    dictionary = make_dictionary({"œdipe"})

    assert dictionary.ligaturize("anaphore") == "anaphore"


def test_accentize_unambiguous_word():
    dictionary = make_dictionary({"évaluation"})

    assert dictionary.accentize("evaluation") == "évaluation"
    assert dictionary.accentize("Evaluation") == "Évaluation"
    assert dictionary.accentize("EVALUATION") == "ÉVALUATION"


def test_accentize_respects_existing_diacritics():
    dictionary = make_dictionary({"élève", "élevé"})

    assert dictionary.accentize("elève") == "élève"
    assert dictionary.accentize("élève") == "élève"


def test_accentize_returns_original_when_ambiguous():
    dictionary = make_dictionary({"élève", "élevé"})

    assert dictionary.accentize("eleve") == "eleve"


def test_accentize_handles_uppercase_fallback():
    dictionary = Dictionary()
    dictionary._prepare_attempted = True  # avoid automatic downloads during tests

    assert dictionary.accentize("NOEL") == "NOËL"


def test_contains_returns_sorted_matches():
    dictionary = make_dictionary({"œuvre", "cœur", "autre"})

    assert dictionary.contains("œ") == ("cœur", "œuvre")


def test_dictionary_loads_static_artifact(tmp_path):
    artifact = tmp_path / "morphalou_data.json.gz"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": "2024-01-01T00:00:00Z",
        "source": {"listing_url": "", "zip_pattern": ""},
        "stats": {"word_count": 2, "ligature_entries": 1, "accent_entries": 1},
        "words": ["oeuvre", "TEST"],
        "ligature_map": {"oeuvre": "œuvre"},
        "accent_map": {"test": ["test", "tést"]},
    }
    with gzip.open(artifact, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)

    dictionary = Dictionary(use_static_data=True, data_path=artifact)

    assert dictionary.ligaturize("oeuvre") == "œuvre"
    assert dictionary.accentize("TEST") == "TÉST"
    assert "œuvre" in dictionary.words


def test_dictionary_cleanup_removes_temp_dir():
    dictionary = Dictionary()
    workdir = dictionary.workdir
    assert workdir.exists()
    dictionary.cleanup()
    assert not workdir.exists()
