# Liste

En français on n'utilise pas le caractère `•` pour les listes à puces mais le tiret demi-cadratin `–`. Le plugin remplace automatiquement les puces par des tirets :

- Premier
- Deuxième
- Troisième

Sans mise en forme, la liste serait affichée ainsi:

/// html | div[class='no-french']

- Premier
- Deuxième
- Troisième

///

Cette correction est configurable et peut être désactivée :


```yaml
plugins:
  - french:
      enable_css_bullets: false
```