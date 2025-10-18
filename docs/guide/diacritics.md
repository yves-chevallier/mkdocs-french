# Diacritiques

Le plugin détecte les diacritiques manquants sur les capitales. Par exemple, `ECOLE` devient `ÉCOLE` et `CA` devient `ÇA`.

La correction s'appuie sur le dictionnaire [Morphalou](https://repository.ortolang.fr/api/content/morphalou) (téléchargé et mis en cache au premier usage) qui répertorie les formes accentuées les plus fréquentes. Activez-la ainsi :

```yaml
plugins:
  - french:
      diacritics: fix # ou warn ou ignore
```

En mode `warn`, un message est émis sans modifier le texte d'origine. Les mots ambigus (plusieurs formes accentuées possibles) sont volontairement laissés tels quels.

## Exemple

Dans cet exemple, la phrase: « Égrène, ô délégué zélé, l’éphémère mélopée où s’ébattent naïvement les âmes désœuvrées, ébaubies d’être épiées ! » écrite sans diacritiques :

```md
EGRENE, O DELEGUE ZELE, L’EPHEMERE MELOPEE OU S’EBATTENT
NAIVEMENT LES AMES DESOEUVREES, EBAUBIES D’ETRE EPIEES !
```

Est corrigée en :

> EGRENE, O DELEGUE ZELE, L’EPHEMERE MELOPEE OU S’EBATTENT
> NAIVEMENT LES AMES DESOEUVREES, EBAUBIES D’ETRE EPIEES !

!!! warning

    On observe la limite de l'algorithme par l'absence de correction pour "délégué zêlé" en raison de l'ambiguité existante sans contexte additionnel. Un modèle de langage serait nécessaire mais la complexité est -- pour le moment -- hors de portée pour ce plugin.
