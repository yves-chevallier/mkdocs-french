# Casse et typographie courante

Les mois, jours et gentilés s'écrivent en minuscule en français. Le plugin peut corriger ou détecter les erreurs courantes tout en respectant un début de phrase (après un point, un deux-points, etc.), où l'initiale reste naturellement majuscule.

Les noms de pays prennent une majuscule initiale : France, Suisse, Allemagne, Italie, Espagne...

Cette phrase comporte plusieurs erreurs : Lundi, Lucas est venu de france ; mais Mardi 5 Novembre, il a rencontré Monsieur Dupont, qui est Français à Paris.

Les avertissements sont reportés lors de la compilation :

```text
WARNING -  [fr-typo:casse] index.md: Casse incorrecte pour «Novembre» → «novembre»
WARNING -  [fr-typo:casse] index.md: Casse incorrecte pour «Mardi» → «mardi»
WARNING -  [fr-typo:casse] index.md: Casse incorrecte pour «Français» → «français»
WARNING -  [fr-typo:casse] index.md: Casse incorrecte pour le pays «france» → «France»
```

La configuration est la suivante:

```yaml
plugins:
  - french:
      casse: warn # ou fix ou ignore
```
