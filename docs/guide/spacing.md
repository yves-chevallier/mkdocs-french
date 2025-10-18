# Espacement et ponctuation

## Ponctuations

En français, les ponctuations doubles sont précédées d'une espace insécable U+202F. Markdown ne le gère pas nativement. Si l'éditeur ajoute manuellement une espace comme dans `ceci :`, le risque est que le rendu HTML puisse ajouter une césure de ligne entre le mot et la ponctuation. Inversément, si l'éditeur n'ajoute pas d'espace, le rendu n'est pas correct. Il n'y a donc pas de solution à l'édition à moins de veiller à ajouter une espace insécable manuellement.

Le plugin ajoute automatiquement une espace insécable U+202F avant les ponctuations doubles: `; ! ?` et une espace fine inssécable U+00A0 avant les deux-points `:`.

Les points de suspension `...` sont remplacés par le caractère Unicode U+2026 `…`.

Les guillemets français `« »` sont également gérés. Le plugin ajoute une espace insécable après le guillemet ouvrant et avant le guillemet fermant. Il remplacera également les guillemets droits `"` par des guillemets français.

L'apostrophe droite `'` U+0027 est remplacée par l'apostrophe typographique U+2019 `’` pour l'élision comme dans "l'homme" ou "aujourd'hui". Ceci permet la selection correcte du mot dans certains navigateurs et garantit l'absence de césure.

Le tiret cadratin `—` U+2014 est utilisé pour les incises et dialogues. Il n'est pas courant en anglais, et a fortiori pas nativement disponible en Markdown. Le plugin remplace automatiquement chaque double tiret `--` par un tiret cadratin.

Certaines contractions avec la virgule ou le point sont également corrigées :

| Incorrect | Correct | Description                                                         |
| --------- | ------- | ------------------------------------------------------------------- |
| ?.        | ?       | Suppression de la ponctuation finale après un point d'interrogation |
| !.        | !       | Suppression de la ponctuation finale après un point d'exclamation   |
| etc..     | etc.    | Suppression de la ponctuation finale après "etc."                   |
| etc...    | etc.    | Suppression de la redondance des points de suspension               |
| etc....   | etc.    | Suppression de la ponctuation finale après "etc."                   |
| m, ...    | m...    | Suppression de la virgule avant "..."                               |

La configuration dans `mkdocs.yml` s'effectue ainsi:

```yaml
plugins:
  - french:
      punctuation: fix # ou warn ou ignore
```

## Exemple

La phrase suivante comporte plusieurs erreurs de ponctuation :

```md
Tu n'as pas pris ton parapluie?. Tante Jeanette -- qui
n'est plus si jeune -- dirait encore: "Tu vas encore te
faire mouiller, etc..."
```

Est corrigée en :

> Tu n'as pas pris ton parapluie?. Tante Jeanette -- qui
> n'est plus si jeune -- dirait encore: "Tu vas encore te
> faire mouiller, etc..."

## Unités

Le plugin ajoute une espace insécable (U+202F) entre les nombres et les unités courantes comme `kg`, `cm`, `m`, `km`, `g`, `L`, `h`, `min`, `s` et les symboles monétaires comme `€`, `$`, `£`, `¥`.

Par exemple `100km` est corrigé en `100 km`. Si vous souhaitez conserver la forme originale, entourez la valeur d'un élément ignoré (`<span>100km</span>` par exemple).

La configuration s'effectue ainsi:

```yaml
plugins:
  - french:
      units: fix # ou warn ou ignore
```