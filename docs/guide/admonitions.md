# Admonitions

Les *admonitions* ne sont pas traduites dans MkDocs, ni dans MkDocs Material. Le plugin corrige automatiquement les titres des admonitions standards comme celle d'un avertissement:

```markdown
!!! warning

    Alerte rouge !
```

qui est interprêté comme:

!!! warning

    Alerte rouge !

Il est possible de configurer le plugin pour traduire les admonitions standards, et spécifier des traductions personnalisées pour des admonitions non standards:

```yaml
plugins:
  - french:
      admonitions: fix # ou warn ou ignore
      admonition_translations:
        pied-piper: "Joueur de flûte" # Pour les admonitions personnalisées
```

/// html | div[style='display: flex; flex-wrap: wrap; gap: 10px; justify-content: space-evenly;']

!!! info inline

    Information

!!! warning inline

    Avertissement

!!! danger inline

    Danger

!!! example inline

    Exemple

!!! note inline

    Note

!!! tip inline

    Astuce

!!! bug inline

    Bug

!!! pied-piper inline

    Admonition personnalisée

///