from __future__ import annotations

from mkdocs_plugin_french.dictionary import Dictionary


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
    dictionary._prepare_attempted = True  # éviter tout téléchargement automatique

    assert dictionary.accentize("NOEL") == "NOËL"


def test_contains_returns_sorted_matches():
    dictionary = make_dictionary({"œuvre", "cœur", "autre"})

    assert dictionary.contains("œ") == ("cœur", "œuvre")
