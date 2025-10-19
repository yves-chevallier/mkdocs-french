# Installation

Pour installer le plugin, utilisez pip:

```bash
pip install mkdocs-french
```

Ensuite, ajoutez le plugin à la configuration de votre site MkDocs dans le fichier `mkdocs.yml`:

```yaml
plugins:
  - french
```

Veillez à bien indiquer la langue de votre documentation. Pour MkDocs Material, ajoutez également la configuration de la langue dans la section `theme`:

```yaml
theme:
  name: material
  language: fr
```

Pour le thème par défaut de MkDocs, ajoutez la configuration de la langue dans la section `site`:

```yaml
site:
  language: fr
```

## Corriger les fichiers sources

Pour corriger les fichiers sources existants, vous pouvez utiliser la commande suivante:
