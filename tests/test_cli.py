from __future__ import annotations

import importlib
from pathlib import Path

from mkdocs_french.cli import main


def test_cli_build_command(monkeypatch, tmp_path):
    target = tmp_path / "artifact.gz"

    def fake_build(path: Path | None, *, force: bool, quiet: bool):
        assert path == target
        assert force
        assert not quiet
        target.write_bytes(b"data")
        return target

    monkeypatch.setattr("mkdocs_french.cli.build_morphalou_artifact", fake_build)

    exit_code = main(["build", "--output", str(target), "--force"])
    assert exit_code == 0
    assert target.read_bytes() == b"data"


def test_cli_without_command_shows_help(capsys):
    exit_code = main([])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "mkdocs-french" in captured.err


def test_module_main_imports_cli_main():
    module = importlib.import_module("mkdocs_french.__main__")
    assert module.main is main
