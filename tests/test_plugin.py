from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from mkdocs_french.constants import DEFAULT_ADMONITION_TRANSLATIONS, NBSP, NNBSP
from mkdocs_french.plugin import Level
from mkdocs_french.rules.base import Rule
from mkdocs_french.rules.orchestrator import RuleOrchestrator, RuleWarning


class DummyRule(Rule):
    def __init__(self, *, detector=None, fixer=None) -> None:
        super().__init__(name="dummy", config_attr="spacing")
        self._detector = detector or (lambda text: [])
        self._fixer = fixer or (lambda text: text)
        self.detect_called = False
        self.fix_called = False

    def detect(self, text: str):
        self.detect_called = True
        return self._detector(text)

    def fix(self, text: str) -> str:
        self.fix_called = True
        return self._fixer(text)


def test_on_config_updates_extra_and_translations(tmp_path, plugin_factory):
    plugin = plugin_factory(
        enable_css_bullets=True, admonition_translations={"warning": "Attention"}
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
    assert not css_path.exists()
    assert plugin._admonition_translations["warning"] == "Attention"
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


def test_on_config_adds_justify_css(tmp_path, plugin_factory):
    plugin = plugin_factory(enable_css_bullets=False, justify=True)
    docs_dir = tmp_path / "docs"
    site_dir = tmp_path / "site"
    mkdocs_config = {
        "docs_dir": str(docs_dir),
        "site_dir": str(site_dir),
        "extra_css": [],
    }

    plugin.on_config(mkdocs_config)

    assert "css/french-justify.css" in mkdocs_config["extra_css"]


def test_on_config_supports_mkdocs_config_object(tmp_path, plugin_factory):
    plugin = plugin_factory(enable_css_bullets=True)
    site_dir = tmp_path / "site"

    class DummyMkDocsConfig:
        def __init__(self, site_dir):
            self.site_dir = str(site_dir)
            self.extra_css = []

        def __getitem__(self, key):
            if key == "site_dir":
                return self.site_dir
            if key == "extra_css":
                return self.extra_css
            raise KeyError(key)

    config_obj = DummyMkDocsConfig(site_dir)

    plugin.on_config(config_obj)

    assert "css/french-bullet.css" in config_obj.extra_css
    assert plugin._site_dir == site_dir


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
    assert not docs_css.exists()

    plugin.on_post_build({"site_dir": str(site_dir)})

    site_css = site_dir / "css" / "french-bullet.css"
    assert site_css.exists()


def test_print_summary_with_rich(monkeypatch, plugin_factory):
    plugin = plugin_factory(summary=True)
    plugin._collected_warnings = [
        {
            "rule": "spacing",
            "file": "doc.md",
            "line": 3,
            "message": "Espace fine",
            "preview": ";",
        }
    ]

    class DummyTable:
        def __init__(self, *args, **kwargs):
            self.rows = []

        def add_column(self, *args, **kwargs):
            return None

        def add_row(self, *args, **kwargs):
            self.rows.append(args)

    class DummyConsole:
        def __init__(self):
            self.rendered = []

        def print(self, table):
            self.rendered.append(table)

    monkeypatch.setattr("mkdocs_french.plugin.Table", DummyTable)
    monkeypatch.setattr("mkdocs_french.plugin.Console", DummyConsole)
    monkeypatch.setattr(
        "mkdocs_french.plugin.box", type("_Box", (), {"ROUNDED": object()})
    )

    plugin._print_summary()

    assert isinstance(plugin._collected_warnings[0], dict)


def test_print_plain_summary_outputs(capsys, plugin_factory):
    plugin = plugin_factory(summary=True)
    plugin._collected_warnings = [
        {
            "rule": "spacing",
            "file": "doc.md",
            "line": 2,
            "message": "Espace fine",
            "preview": ";",
        }
    ]

    plugin._print_plain_summary()

    captured = capsys.readouterr()
    assert "Résumé des avertissements" in captured.out


def test_orchestrator_ignore_returns_original_text():
    rule = DummyRule(fixer=lambda text: text + "!")
    orchestrator = RuleOrchestrator([rule])

    processed, warnings = orchestrator.process("Text", lambda _rule: Level.ignore)

    assert processed == "Text"
    assert warnings == []
    assert not rule.detect_called
    assert not rule.fix_called


def test_orchestrator_warn_collects_warnings():
    rule = DummyRule(detector=lambda text: [(0, len(text), "Message de test", "fixe")])
    orchestrator = RuleOrchestrator([rule])

    processed, warnings = orchestrator.process("texte", lambda _rule: Level.warn)

    assert processed == "texte"
    assert len(warnings) == 1
    warning = warnings[0]
    assert warning.message == "Message de test"
    assert warning.preview == "fixe"
    assert rule.detect_called
    assert not rule.fix_called


def test_orchestrator_fix_uses_fixer():
    rule = DummyRule(fixer=lambda text: text.upper())
    orchestrator = RuleOrchestrator([rule])

    processed, warnings = orchestrator.process("abc", lambda _rule: Level.fix)

    assert processed == "ABC"
    assert warnings == []
    assert rule.fix_called
    assert not rule.detect_called


def test_emit_warnings_logs_and_collects_summary(plugin_factory, caplog):
    plugin = plugin_factory(summary=True)
    rule = DummyRule()
    warning = RuleWarning(
        rule=rule,
        start=0,
        end=5,
        message="Message de test",
        preview="fixe",
    )

    with caplog.at_level(logging.WARNING, logger="mkdocs.plugins.fr_typo"):
        plugin._emit_warnings([warning], "docs/page.md", 7)

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

    assert plugin.on_page_markdown(markdown_text, page, {}, None) == markdown_text


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
        casse=Level.ignore, diacritics=Level.ignore, units=Level.ignore
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
    html = '<p>Normal: test!</p><p class="fr-typo-ignore">Ignorer: test!</p>'

    result = plugin.on_page_content(html, page, {}, None)
    soup = BeautifulSoup(result, "html.parser")
    texts = [p.get_text() for p in soup.find_all("p")]

    assert texts[0] == f"Normal{NBSP}: test{NNBSP}!"
    assert texts[1] == "Ignorer: test!"


def test_on_page_content_applies_foreign_italicization(plugin_factory, page):
    plugin = plugin_factory()
    html = "<p>Le chanteur a capella a été diplômé honoris causa par l'université.</p>"

    result = plugin.on_page_content(html, page, {}, None)
    soup = BeautifulSoup(result, "html.parser")

    italics = [em.get_text() for em in soup.find_all("em")]
    assert "a capella" in italics
    assert "honoris causa" in italics


def test_on_page_content_applies_foreign_in_italic_context(plugin_factory, page):
    plugin = plugin_factory()
    html = "<p><em>Avec cette distinction, je serai de facto plus riche.</em></p>"

    result = plugin.on_page_content(html, page, {}, None)
    soup = BeautifulSoup(result, "html.parser")

    em = soup.find("em")
    span = em.find("span")
    assert span is not None
    assert span.get_text() == "de facto"
    assert span.get("style") == "font-style: normal;"


def test_on_page_content_foreign_warns_without_fix(plugin_factory, page, caplog):
    plugin = plugin_factory(foreign=Level.warn)
    html = "<p>Il a agi de facto.</p>"

    with caplog.at_level(logging.WARNING, logger="mkdocs.plugins.fr_typo"):
        plugin.on_page_content(html, page, {}, None)

    assert "Locution étrangère non italique : «de facto»" in caplog.text


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

    monkeypatch.setattr("mkdocs_french.plugin.Console", None)
    monkeypatch.setattr("mkdocs_french.plugin.Table", None)
    monkeypatch.setattr("mkdocs_french.plugin.box", None)

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
        plugin, "!!! warning\n    attention\n", page, extensions=["admonition"]
    )

    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one(".admonition-title").get_text()
    assert title == DEFAULT_ADMONITION_TRANSLATIONS["warning"]
