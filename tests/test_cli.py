from __future__ import annotations

import importlib
from pathlib import Path

from mkdocs_french import cli as cli_module
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


def test_cli_check_reports_issues(tmp_path, capsys):
    docs_dir = tmp_path / "sources"
    docs_dir.mkdir()
    md_path = docs_dir / "page.md"
    md_path.write_text(
        "C a d que le chanteur a capella voyage en france.\n",
        encoding="utf-8",
    )

    exit_code = main(["check", "--docs-dir", str(docs_dir)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "page.md" in captured.out
    assert "[abbreviation]" in captured.out
    assert "[foreign]" in captured.out


def test_cli_fix_updates_files(tmp_path, capsys):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    md_path = docs_dir / "page.md"
    md_path.write_text(
        "C a d que le chanteur a capella voyage en france.\n",
        encoding="utf-8",
    )

    exit_code = main(["fix", "--docs-dir", str(docs_dir)])
    captured_fix = capsys.readouterr()

    assert exit_code == 0
    assert "Corrigé" in captured_fix.out

    updated = md_path.read_text(encoding="utf-8")
    assert "c.-à-d." in updated
    assert "_a capella_" in updated
    assert "France" in updated

    exit_code_check = main(["check", "--docs-dir", str(docs_dir)])
    captured_check = capsys.readouterr()
    assert exit_code_check == 0
    assert "Aucune correction nécessaire." in captured_check.out


def test_cli_check_missing_directory(tmp_path, capsys):
    missing = tmp_path / "absent"

    exit_code = main(["check", "--docs-dir", str(missing)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Directory not found" in captured.err


def test_cli_build_quiet_mode(monkeypatch, tmp_path, capsys):
    target = tmp_path / "artifact.gz"

    def fake_build(path: Path | None, *, force: bool, quiet: bool):
        assert quiet
        path = path or target
        path.write_bytes(b"data")
        return path

    monkeypatch.setattr("mkdocs_french.cli.build_morphalou_artifact", fake_build)

    exit_code = main(["build", "--output", str(target), "--quiet"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ""
    assert target.exists()


def test_cli_build_failure_is_reported(monkeypatch, capsys):
    def fake_build(path: Path | None, *, force: bool, quiet: bool):
        raise RuntimeError("boom")

    monkeypatch.setattr("mkdocs_french.cli.build_morphalou_artifact", fake_build)

    exit_code = main(["build"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error: boom" in captured.err


def test_cli_fix_missing_directory(tmp_path, capsys):
    missing = tmp_path / "absent"

    exit_code = main(["fix", "--docs-dir", str(missing)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Directory not found" in captured.err


def test_cli_fix_reports_no_changes(tmp_path, capsys):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "page.md").write_text("Texte conforme.\n", encoding="utf-8")

    exit_code = main(["fix", "--docs-dir", str(docs_dir)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Aucune correction appliquée" in captured.out


def test_format_relative_handles_external_path(tmp_path):
    outside = tmp_path / "outer" / "file.md"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("x", encoding="utf-8")

    result = cli_module._format_relative(outside, tmp_path / "docs")

    assert result == str(outside)
