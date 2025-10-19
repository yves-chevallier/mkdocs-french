# Casse et typographie courante

Les mois, jours et gentilés s'écrivent en minuscule en français. Le plugin peut corriger ou détecter les erreurs courantes tout en respectant un début de phrase (après un point, un deux-points, etc.), où l'initiale reste naturellement majuscule. Un `C` isolé n'est pas transformé en «Ç» afin de ne pas détériorer les acronymes ou les listes.

Par défaut, la remise en majuscule automatique des noms de pays est désactivée : sans contexte, elle entraînait trop de faux positifs. Conservez cette vérification manuellement si vous en avez l'usage.

Cette phrase comporte plusieurs erreurs : Lundi, Lucas est venu ; mais Mardi 5 Novembre, il a rencontré Monsieur Dupont, qui est Français à Paris.

Les avertissements sont reportés lors de la compilation :

```text
WARNING -  [fr-typo:casse] index.md: Casse incorrecte pour «Novembre» → «novembre»
WARNING -  [fr-typo:casse] index.md: Casse incorrecte pour «Mardi» → «mardi»
WARNING -  [fr-typo:casse] index.md: Casse incorrecte pour «Français» → «français»
```

Sans contexte lexical, certains faux positifs restent possibles (par exemple «Mars» quand il désigne la planète). Vérifiez les alertes avant d'appliquer une correction automatique.

La configuration est la suivante :

```yaml
plugins:
  - french:
      casse: warn # ou fix ou ignore
```
