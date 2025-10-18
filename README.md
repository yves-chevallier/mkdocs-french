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

Activate the plugin in your `mkdocs.yml`:

```yaml
plugins:
  - french:
```

## Développement avec uv

Le projet utilise [uv](https://github.com/astral-sh/uv) pour la gestion des dépendances.

```bash
# Installer les dépendances (runtime + extras de développement)
uv sync --extra dev

# Lancer la suite de tests
uv run pytest

# Construire la documentation MkDocs en local
uv run mkdocs serve
```

## Données Morphalou pré-générées

Le plugin ne télécharge plus Morphalou à chaque exécution.
Il charge un artéfact compressé localisé dans `mkdocs_french/artifacts/morphalou_data.json.gz`.
L’archive est générée pendant le processus de packaging et livrée dans les wheels publiées.
Si vous utilisez le dépôt source, générez l’artéfact avant d’exécuter MkDocs.

### Générer les artéfacts

Utilisez la commande suivante (avec l'environnement uv configuré) :

```bash
uv run python -m mkdocs_french build
```

L’option `--force` permet d’écraser un artéfact existant, et `--output` accepte un chemin personnalisé.
Dans un pipeline CI, exécutez la commande avant MkDocs ; elle ne recrée pas le fichier si celui-ci est déjà présent.

## Comportement de configuration du plugin

Le hook `on_config` du plugin peut recevoir soit un dictionnaire Python brut,
soit l'objet `MkDocsConfig` fourni par MkDocs. Cette distinction est
particulièrement visible dans la suite de tests, qui instancie parfois le
plugin avec une configuration minimale basée sur un dict.

Pour assurer la compatibilité avec ces deux scénarios, le plugin détecte le
type de `config` avant de lire `site_dir` et de mettre à jour la liste
`extra_css`. Un accès via `config.setdefault` ne fonctionne que pour un dict,
alors que `MkDocsConfig` expose `site_dir` comme attribut mais ne propose pas de
méthode `setdefault`. Sans cette précaution, l'appel échouerait côté tests et le
plugin ne pourrait pas s'exécuter correctement dans un environnement MkDocs
réel.

La logique actuelle garantit en plus qu'une feuille de style ajoutée par le
plugin n'est insérée qu'une seule fois dans `extra_css`, même si la commande de
build est relancée dans le même processus. On évite ainsi la duplication de
chemins dans la configuration finale.
