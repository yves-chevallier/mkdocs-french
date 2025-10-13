from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import markdown
import pytest

# ---------------------------------------------------------------------------
# Provide minimal mkdocs stubs so the plugin can be imported without mkdocs
# being installed in the current test environment. If mkdocs is available we
# simply use the real package.
# ---------------------------------------------------------------------------
try:  # pragma: no cover - executed only when mkdocs is installed
    import mkdocs  # type: ignore  # noqa: F401
except ImportError:  # pragma: no cover - exercised when mkdocs missing
    mkdocs_module = types.ModuleType("mkdocs")

    config_module = types.ModuleType("mkdocs.config")
    config_options_module = types.ModuleType("mkdocs.config.config_options")
    config_base_module = types.ModuleType("mkdocs.config.base")
    plugins_module = types.ModuleType("mkdocs.plugins")

    class _DummyOption:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

    class Choice(_DummyOption):
        pass

    class Type(_DummyOption):
        pass

    config_options_module.Choice = Choice  # type: ignore[attr-defined]
    config_options_module.Type = Type  # type: ignore[attr-defined]

    class Config(dict):  # minimal placeholder
        pass

    config_base_module.Config = Config  # type: ignore[attr-defined]

    class BasePlugin:  # minimal generic-compatible stub
        config_scheme = ()

        def __init__(self) -> None:
            self.config = {}

        def __class_getitem__(cls, item):  # type: ignore[override]
            return cls

    plugins_module.BasePlugin = BasePlugin  # type: ignore[attr-defined]

    mkdocs_module.config = config_module  # type: ignore[attr-defined]

    sys.modules["mkdocs"] = mkdocs_module
    sys.modules["mkdocs.config"] = config_module
    sys.modules["mkdocs.config.config_options"] = config_options_module
    sys.modules["mkdocs.config.base"] = config_base_module
    sys.modules["mkdocs.plugins"] = plugins_module

from mkdocs_plugin_french.constants import DEFAULT_ADMONITION_TRANSLATIONS
from mkdocs_plugin_french.plugin import FrenchPlugin, Level


def make_plugin_config(**overrides):
    """Create a lightweight config namespace for the plugin."""
    defaults = {
        "abbreviation": Level.fix,
        "ordinaux": Level.fix,
        "ligatures": Level.ignore,
        "casse": Level.warn,
        "spacing": Level.fix,
        "quotes": Level.fix,
        "units": Level.fix,
        "diacritics": Level.warn,
        "foreign": Level.fix,
        "enable_css_bullets": False,  # disabled by default in tests
        "css_scope_selector": "body",
        "admonitions": Level.fix,
        "admonition_translations": {},
        "summary": False,
        "force_line_markers": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.fixture
def plugin_factory():
    def factory(**config_overrides):
        plugin = FrenchPlugin()
        plugin.config = make_plugin_config(**config_overrides)
        plugin._collected_warnings = []
        plugin._temp_css_created = set()
        plugin._admonition_translations = DEFAULT_ADMONITION_TRANSLATIONS.copy()
        return plugin

    return factory


@pytest.fixture
def page(tmp_path):
    src_file = tmp_path / "docs" / "index.md"
    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text("# Dummy page\n", encoding="utf-8")
    return SimpleNamespace(
        file=SimpleNamespace(
            src_path="docs/index.md",
            abs_src_path=str(src_file),
        )
    )


@pytest.fixture
def render_with_plugin():
    def renderer(plugin: FrenchPlugin, markdown_text: str, page, *, extensions=None):
        extensions = extensions or []
        processed_md = plugin.on_page_markdown(markdown_text, page, {}, None)
        html = markdown.markdown(processed_md, extensions=extensions)
        return plugin.on_page_content(html, page, {}, None)

    return renderer
