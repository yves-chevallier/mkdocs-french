# MkDocs french Plugin

[![CI](https://github.com/yves-chevallier/mkdocs-french/actions/workflows/ci.yml/badge.svg)](https://github.com/yves-chevallier/mkdocs-french/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/yves-chevallier/mkdocs-french/branch/main/graph/badge.svg)](https://codecov.io/gh/yves-chevallier/mkdocs-french)
[![PyPI](https://img.shields.io/pypi/v/mkdocs-french.svg)](https://pypi.org/project/mkdocs-french/)
[![Repo Size](https://img.shields.io/github/repo-size/yves-chevallier/mkdocs-french.svg)](https://github.com/yves-chevallier/mkdocs-french)
[![Python Versions](https://img.shields.io/pypi/pyversions/mkdocs-french.svg?logo=python)](https://pypi.org/project/mkdocs-french/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)

![MkDocs](https://img.shields.io/badge/MkDocs-1.6+-blue.svg?logo=mkdocs)
![MkDocs Material](https://img.shields.io/badge/MkDocs%20Material-supported-success.svg?logo=materialdesign)
![french](https://img.shields.io/badge/french-API-lightgrey.svg?logo=french)
![Python](https://img.shields.io/badge/Python-typed-blue.svg?logo=python)

This plugin is meant to improve MkDocs documentation written in French by checking and fixing common typographical and writing issues according to French language rules. It can detect and fix the following common issues:

- Abbreviations (e.g., "M." to "M.", "Dr" to "Dr", etc.)
- Ordinals (e.g., "1er" to "1er", "2e" to "2e", etc.)
- Ligatures (e.g., "œ" to "œ", "æ" to "æ", etc.)
- Case (e.g., "Lundi" to "lundi", "France" to "France", etc.)
- Spacing (e.g., before punctuation marks)
- Quotes (e.g., « guillemets »)
- Units (e.g., "10 km" to "10 km", "5 kg" to "5 kg", etc.)
- Diacritics (e.g., "é" to "é", "à" to "à", etc.)
- Admonitions (e.g., translating admonition titles to French)

## Installation

```bash
pip install mkdocs-french
```

Activate the plugin in your `mkdocs.yml`:

```yaml
plugins:
  - french:
```

Install the plugin using pip:

```bash
pip install mkdocs-french
```
