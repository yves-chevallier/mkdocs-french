# Configuration

La configuration du plugin se fait via le fichier `mkdocs.yml` à la racine de votre projet MkDocs. Au minimum, vous devez spécifier le nom du plugin et son emplacement dans la section `plugins`. Voici un exemple de configuration minimale :

```yaml
plugins:
  - french
```

## Options de configuration

Le plugin `mkdocs-french` offre plusieurs options de configuration pour personnaliser son comportement. Voici une liste des options disponibles avec leurs descriptions :

```yaml
plugins:
  - french:
      abbreviation: fix # fix, ignore, warn
      ordinaux: fix # fix, ignore, warn
      ligatures: ignore # fix, ignore, warn
      casse: warn # fix, ignore, warn
      spacing: fix # fix, ignore, warn
      quotes: fix # fix, ignore, warn
      units: fix # fix, ignore, warn
      diacritics: warn # fix, ignore, warn
      enable_css_bullets: true
      css_scope_selector: "body"
      admonitions: fix # fix, ignore, warn
      admonition_translations:
        pied-piper: "Joueur de flûte" # custom translation

      # Affiche un résumé des modifications en fin de compilation
      summary: false

      # Affiche des marqueurs dans le texte pour chaque correction effectuée
      force_line_markers: false
```
