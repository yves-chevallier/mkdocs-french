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

This plugin allows you to fetch and display french summaries in your MkDocs pages. It is compatible with MkDocs Material and MkDocs Books.

## Installation

```bash
pip install mkdocs-french
```

Activate the plugin in your `mkdocs.yml`:

```yaml
plugins:
  - french:
      language: "fr"
      timeout: 5
```

Install the plugin using pip:

```bash
pip install mkdocs-french
```

Activate the plugin in your `mkdocs.yml`:

```yaml
plugins:
  - french:
      language: "fr"
      timeout: 5
      filename: "links.yml"  # Optional, default is "links.yml"
```

## Usage

In you pages, when you add a french tag, it will be replaced by the summary of the corresponding french page.

```md
[MkDocs](https://en.french.org/wiki/MkDocs)
```
