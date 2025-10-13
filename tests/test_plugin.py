from __future__ import annotations

import logging

import pytest
from bs4 import BeautifulSoup

from mkdocs_plugin_french.constants import DEFAULT_ADMONITION_TRANSLATIONS, NBSP, NNBSP
from mkdocs_plugin_french.plugin import Level
from mkdocs_plugin_french.rules.base import RuleDefinition


def test_on_config_copies_css_and_updates_extra(tmp_path, plugin_factory):
    plugin = plugin_factory(
        enable_css_bullets=True,
        admonition_translations={"warning": "Attention"},
    )
    docs_dir = tmp_path / "docs"
    site_dir = tmp_path / "site"
    mkdocs_config = {
        "docs_dir": str(docs_dir),
        "site_dir": str(site_dir),
        "extra_css": ["base.css"],
    }

    plugin.on_config(mkdocs_config)

    css_path = docs_dir / "css" / "french-bullet.css"
    assert css_path.exists()
    assert plugin._admonition_translations["warning"] == "Attention"
    assert css_path in plugin._temp_css_created
    assert mkdocs_config["extra_css"] == ["base.css", "css/french-bullet.css"]


def test_on_config_does_not_duplicate_extra_css(tmp_path, plugin_factory):
    plugin = plugin_factory(enable_css_bullets=True)
    docs_dir = tmp_path / "docs"
    site_dir = tmp_path / "site"
    mkdocs_config = {
        "docs_dir": str(docs_dir),
        "site_dir": str(site_dir),
        "extra_css": ["css/french-bullet.css"],
    }

    plugin.on_config(mkdocs_config)

    assert mkdocs_config["extra_css"].count("css/french-bullet.css") == 1


def test_on_post_build_copies_assets_and_cleans(tmp_path, plugin_factory):
    plugin = plugin_factory(enable_css_bullets=True)
    docs_dir = tmp_path / "docs"
    site_dir = tmp_path / "site"
    mkdocs_config = {
        "docs_dir": str(docs_dir),
        "site_dir": str(site_dir),
        "extra_css": [],
    }

    plugin.on_config(mkdocs_config)
    docs_css = docs_dir / "css" / "french-bullet.css"
    assert docs_css.exists()

    plugin.on_post_build({"site_dir": str(site_dir)})

    site_css = site_dir / "css" / "french-bullet.css"
    assert site_css.exists()
    assert not docs_css.exists()
    assert not (docs_dir / "css").exists()
    assert plugin._temp_css_created == set()


def test_apply_rule_ignore_returns_original_text(plugin_factory):
    plugin = plugin_factory()

    rule = RuleDefinition(
        name="dummy",
        config_attr="spacing",
        detector=lambda text: [],
        fixer=lambda text: text + "!",
    )

    original = "Text"
    assert plugin._apply_rule(rule, Level.ignore, original, "page.md", 1) == original


def test_apply_rule_warn_logs_and_collects_summary(plugin_factory, caplog):
    plugin = plugin_factory(summary=True)

    def detector(text):
        return [(0, 5, "Message de test", "fixe")]

    rule = RuleDefinition(
        name="dummy",
        config_attr="spacing",
        detector=detector,
        fixer=lambda text: text,
    )

    with caplog.at_level(logging.WARNING, logger="mkdocs.plugins.fr_typo"):
        result = plugin._apply_rule(rule, Level.warn, "texte", "docs/page.md", 7)

    assert result == "texte"
    assert "Message de test" in caplog.text
    assert plugin._collected_warnings == [
        {
            "rule": "dummy",
            "file": "docs/page.md",
            "line": 7,
            "message": "Message de test",
            "preview": "fixe",
        }
    ]


def test_apply_rule_fix_uses_fixer(plugin_factory):
    plugin = plugin_factory()

    rule = RuleDefinition(
        name="uppercase",
        config_attr="spacing",
        detector=lambda text: [],
        fixer=lambda text: text.upper(),
    )

    assert plugin._apply_rule(rule, Level.fix, "abc", "page.md", None) == "ABC"


def test_on_page_markdown_translates_admonition_title(plugin_factory, page):
    plugin = plugin_factory()
    markdown_text = "!!! warning\n    Attention\n"

    result = plugin.on_page_markdown(markdown_text, page, {}, None)

    first_line = result.splitlines()[0]
    assert first_line == f'!!! warning "{DEFAULT_ADMONITION_TRANSLATIONS["warning"]}"'


def test_on_page_markdown_preserves_existing_title(plugin_factory, page):
    plugin = plugin_factory()
    markdown_text = '!!! warning "Titre existant"\n    Corps\n'

    result = plugin.on_page_markdown(markdown_text, page, {}, None)

    assert result.splitlines()[0] == '!!! warning "Titre existant"'


def test_on_page_markdown_skips_when_disabled(plugin_factory, page):
    plugin = plugin_factory(admonitions=Level.ignore)
    markdown_text = "!!! warning\n    Attention\n"

    assert (
        plugin.on_page_markdown(markdown_text, page, {}, None) == markdown_text
    )


def test_on_page_content_applies_spacing_rule(plugin_factory, page):
    plugin = plugin_factory(
        abbreviation=Level.ignore,
        ordinaux=Level.ignore,
        ligatures=Level.ignore,
        casse=Level.ignore,
        spacing=Level.fix,
        quotes=Level.ignore,
        units=Level.ignore,
        diacritics=Level.ignore,
    )
    html = "<p>Bonjour: test!</p>"

    result = plugin.on_page_content(html, page, {}, None)
    soup = BeautifulSoup(result, "html.parser")

    assert soup.p.get_text() == f"Bonjour{NBSP}: test{NNBSP}!"


def test_on_page_content_respects_ignore_markers(plugin_factory, page):
    plugin = plugin_factory(
        abbreviation=Level.ignore,
        ordinaux=Level.ignore,
        ligatures=Level.ignore,
        casse=Level.ignore,
        spacing=Level.fix,
        quotes=Level.ignore,
        units=Level.ignore,
        diacritics=Level.ignore,
    )
    html = (
        "<p>Premier: test!</p>"
        "<!--fr-typo-ignore-start-->"
        "<p>Ignorer: test!</p>"
        "<!--fr-typo-ignore-end-->"
        "<p>Dernier: test!</p>"
    )

    result = plugin.on_page_content(html, page, {}, None)
    soup = BeautifulSoup(result, "html.parser")
    texts = [p.get_text() for p in soup.find_all("p")]

    assert texts[0] == f"Premier{NBSP}: test{NNBSP}!"
    assert texts[1] == "Ignorer: test!"
    assert texts[2] == f"Dernier{NBSP}: test{NNBSP}!"


def test_on_page_content_handles_documented_spacing_cases(plugin_factory, page):
    plugin = plugin_factory(
        casse=Level.ignore,
        diacritics=Level.ignore,
        units=Level.ignore,
    )
    html = (
        "<p>Tu n'as pas pris ton parapluie!. "
        "Tu vas encore -- te faire mouiller, etc...</p>"
    )

    result = plugin.on_page_content(html, page, {}, None)
    soup = BeautifulSoup(result, "html.parser")

    expected = (
        f"Tu n’as pas pris ton parapluie{NNBSP}! "
        "Tu vas encore — te faire mouiller, etc."
    )
    assert soup.p.get_text() == expected


def test_on_page_content_respects_ignore_classes(plugin_factory, page):
    plugin = plugin_factory(
        abbreviation=Level.ignore,
        ordinaux=Level.ignore,
        ligatures=Level.ignore,
        casse=Level.ignore,
        spacing=Level.fix,
        quotes=Level.ignore,
        units=Level.ignore,
        diacritics=Level.ignore,
    )
    html = (
        "<p>Normal: test!</p>"
        '<p class="fr-typo-ignore">Ignorer: test!</p>'
    )

    result = plugin.on_page_content(html, page, {}, None)
    soup = BeautifulSoup(result, "html.parser")
    texts = [p.get_text() for p in soup.find_all("p")]

    assert texts[0] == f"Normal{NBSP}: test{NNBSP}!"
    assert texts[1] == "Ignorer: test!"


def test_on_page_content_keeps_sentence_start_capital(plugin_factory, page):
    plugin = plugin_factory(
        abbreviation=Level.ignore,
        ordinaux=Level.ignore,
        ligatures=Level.ignore,
        casse=Level.fix,
        spacing=Level.ignore,
        quotes=Level.ignore,
        units=Level.ignore,
        diacritics=Level.ignore,
    )
    html = "<p>Erreur: Lundi, réunion.</p>"

    result = plugin.on_page_content(html, page, {}, None)
    soup = BeautifulSoup(result, "html.parser")

    assert soup.p.get_text() == "Erreur: Lundi, réunion."


def test_on_page_content_uppercases_countries(plugin_factory, page):
    plugin = plugin_factory(
        abbreviation=Level.ignore,
        ordinaux=Level.ignore,
        ligatures=Level.ignore,
        casse=Level.fix,
        spacing=Level.ignore,
        quotes=Level.ignore,
        units=Level.ignore,
        diacritics=Level.ignore,
    )
    html = "<p>voyage en france et espagne</p>"

    result = plugin.on_page_content(html, page, {}, None)
    soup = BeautifulSoup(result, "html.parser")

    assert soup.p.get_text() == "voyage en France et Espagne"


def test_on_post_page_returns_content_as_is(plugin_factory):
    plugin = plugin_factory()
    assert plugin.on_post_page("HTML", None, None) == "HTML"


def test_print_summary_plain_fallback(plugin_factory, capsys, monkeypatch):
    plugin = plugin_factory(summary=True)
    plugin._collected_warnings = [
        {
            "rule": "dummy",
            "file": "docs/page.md",
            "line": 3,
            "message": "Alerte",
            "preview": "texte",
        }
    ]

    monkeypatch.setattr("mkdocs_plugin_french.plugin.Console", None)
    monkeypatch.setattr("mkdocs_plugin_french.plugin.Table", None)
    monkeypatch.setattr("mkdocs_plugin_french.plugin.box", None)

    plugin._print_summary()

    output = capsys.readouterr().out
    assert "Résumé des avertissements typographiques" in output
    assert "[dummy] docs/page.md (Ligne 3)" in output


def test_functional_spacing_render(plugin_factory, page, render_with_plugin):
    plugin = plugin_factory(
        abbreviation=Level.ignore,
        ordinaux=Level.ignore,
        ligatures=Level.ignore,
        casse=Level.ignore,
        spacing=Level.fix,
        quotes=Level.ignore,
        units=Level.ignore,
        diacritics=Level.ignore,
    )

    html = render_with_plugin(plugin, "Bonjour: test!", page)

    assert html == f"<p>Bonjour{NBSP}: test{NNBSP}!</p>"


def test_functional_admonition_translation(plugin_factory, page, render_with_plugin):
    plugin = plugin_factory()

    html = render_with_plugin(
        plugin,
        "!!! warning\n    attention\n",
        page,
        extensions=["admonition"],
    )

    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one(".admonition-title").get_text()
    assert title == DEFAULT_ADMONITION_TRANSLATIONS["warning"]
