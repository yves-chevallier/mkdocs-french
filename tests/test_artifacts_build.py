from __future__ import annotations

import gzip
import json

import pytest

from mkdocs_french.artifacts.build import build_morphalou_artifact


class DummyDictionary:
    def __init__(self, use_static_data: bool = False):
        self.words = {"test"}
        self._ligature_map = {"test": "test"}
        self._accent_map = {"test": ("test",)}

    def prepare(self) -> None:  # pragma: no cover - stub
        pass

    def cleanup(self) -> None:  # pragma: no cover - stub
        pass


def test_build_morphalou_artifact_generates_payload(monkeypatch, tmp_path, capsys):
    target = tmp_path / "artifact.json.gz"

    monkeypatch.setattr(
        "mkdocs_french.artifacts.build.Dictionary", DummyDictionary
    )

    path = build_morphalou_artifact(target, quiet=False)
    assert path == target
    assert target.exists()

    with gzip.open(target, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["schema_version"] >= 1
    assert payload["words"] == ["test"]
    assert payload["ligature_map"] == {"test": "test"}

    captured = capsys.readouterr()
    assert "Downloading" in captured.err


def test_build_morphalou_artifact_refuses_existing_file(monkeypatch, tmp_path):
    target = tmp_path / "artifact.json.gz"
    target.write_bytes(b"existing")

    monkeypatch.setattr(
        "mkdocs_french.artifacts.build.Dictionary", DummyDictionary
    )

    with pytest.raises(FileExistsError):
        build_morphalou_artifact(target, quiet=True)
