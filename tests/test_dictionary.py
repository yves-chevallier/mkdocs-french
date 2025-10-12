from __future__ import annotations

import json
from urllib.error import URLError
import zipfile

import pytest

from mkdocs_plugin_french import dictionary as dict_module
from mkdocs_plugin_french.dictionary import AMBIGUOUS_KEYS, Dictionary, MAP_FILENAME


def test_dictionary_loads_from_cache(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cache_file = cache_dir / MAP_FILENAME
    cache_file.write_text(
        json.dumps({"CAFE": ["café"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(dict_module, "CACHE_DIR", cache_dir)

    dictionary = Dictionary()

    assert dictionary.accentize("cafe") == "café"


def test_dictionary_corrupted_cache_triggers_rebuild(tmp_path, monkeypatch, caplog):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cache_file = cache_dir / MAP_FILENAME
    cache_file.write_text("{invalid}", encoding="utf-8")
    monkeypatch.setattr(dict_module, "CACHE_DIR", cache_dir)

    rebuilt_mapping = {"FRANCAIS": ["Français"]}

    def fake_build(self, target):
        return rebuilt_mapping

    monkeypatch.setattr(Dictionary, "_build_from_source", fake_build)

    dictionary = Dictionary()
    with caplog.at_level("WARNING"):
        assert dictionary.accentize("francais") == "Français"

    assert "cache corrompu" in caplog.text


def test_dictionary_build_from_source_failure_uses_fallback(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr(dict_module, "CACHE_DIR", cache_dir)

    fallback_map = {"ROLE": ["RÔLE"]}

    monkeypatch.setattr(dict_module, "_build_fallback_map", lambda: fallback_map)

    def failing_download(*_args, **_kwargs):
        raise URLError("no network")

    monkeypatch.setattr(dict_module, "urlretrieve", failing_download)

    saved_cache = {}

    def fake_save(cache_file, mapping):
        saved_cache["path"] = cache_file
        saved_cache["mapping"] = mapping
    monkeypatch.setattr(Dictionary, "_save_cache", staticmethod(fake_save))

    dictionary = Dictionary()
    mapping = dictionary._build_from_source(cache_dir / MAP_FILENAME)

    assert mapping == fallback_map
    assert saved_cache["mapping"] == fallback_map
    assert saved_cache["path"].parent == cache_dir


def test_dictionary_build_from_source_success(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr(dict_module, "CACHE_DIR", cache_dir)

    zip_path = cache_dir / dict_module.ZIP_FILENAME
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "Lexique383.tsv",
            "ortho\tfreq\nFrançais\t1\nCafe\t1\nFrançais\t2\n",
        )

    saved_mapping = {}

    def fake_save(cache_file, mapping):
        saved_mapping["path"] = cache_file
        saved_mapping["mapping"] = mapping
    monkeypatch.setattr(Dictionary, "_save_cache", staticmethod(fake_save))

    dictionary = Dictionary()
    mapping = dictionary._build_from_source(cache_dir / MAP_FILENAME)

    assert mapping["FRANCAIS"] == ["Français"]
    assert saved_mapping["path"] == cache_dir / MAP_FILENAME
    assert saved_mapping["mapping"]["FRANCAIS"] == ["Français"]


def test_dictionary_returns_none_for_multiple_candidates():
    dictionary = Dictionary()
    dictionary._map = {"COTE": ["Côte", "Côté"]}

    assert dictionary.accentize("cote") is None


def test_dictionary_respects_ambiguous_keys(monkeypatch):
    dictionary = Dictionary()
    dictionary._map = {key: ["dummy"] for key in AMBIGUOUS_KEYS}

    assert dictionary.accentize("le") is None


@pytest.mark.parametrize(
    "candidates,original,expected",
    [
        (["français", "Français"], "francais", "français"),
        (["FRANÇAIS", "Français"], "FRANCAIS", "FRANÇAIS"),
        (["FRANÇAIS", "Français"], "Francais", "Français"),
    ],
)
def test_choose_candidate_preserves_original_casing(candidates, original, expected):
    assert Dictionary._choose_candidate(candidates, original) == expected
