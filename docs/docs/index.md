# MkDocs French Plugin

## Ponctuation

En français, les ponctuations doubles sont précédées d'une espace insécable. Markdown ne le gère pas nativement. Si l'éditeur ajoute manuellement une espace comme dans `ceci :`, le risque est que le rendu HTML puisse ajouter une césure de ligne entre le mot et la ponctuation. Inversément, si l'éditeur n'ajoute pas d'espace, le rendu n'est pas correct.

Le plugin ajoute automatiquement une espace insécable (U+202F) avant les ponctuations doubles: `; ! ?` et (U+00A0) avant les deux-points `:`.

Les points de suspension `...` sont remplacés par le caractère Unicode U+2026 `…`.

Les guillemets français `« »` sont également gérés. Le plugin ajoute une espace insécable (U+202F) après le guillemet ouvrant et avant le guillemet fermant. Il remplacera également les guillemets droits `"` par des guillemets français.

L'apostrophe droite `'` est remplacée par l'apostrophe typographique U+2019 `’` pour l'élision comme dans "l'homme" ou "aujourd'hui".

Une espace insécable est également nécessaire devant les unités et les symboles monétaires. Le plugin ajoute une espace insécable (U+202F) avant les unités courantes comme `kg`, `cm`, `m`, `km`, `g`, `L`, `h`, `min`, `s` et les symboles monétaires comme `€`, `$`, `£`, `¥`.

## Ligatures

Le plugin remplace automatiquement certaines combinaisons de lettres par des ligatures typographiques courantes en français. Par exemple, "oe" est remplacé par "œ" dans des mots comme "coeur", "oeuvre", "boeuf", "oeil", "oeuf", "oesophage" ou "oelacanthe".

/// html | div[style='float: left; width: 50%; text-align: center;']


| Mot         | Correction |
| ----------- | ---------- |
| <!--fr-typo-ignore-->boeuf<!--/fr-typo-ignore-->       | bœuf       |
| <!--fr-typo-ignore-->caecum<!--/fr-typo-ignore-->      | cæcum      |
| <!--fr-typo-ignore-->cænotype<!--/fr-typo-ignore-->    | cænotype   |
| <!--fr-typo-ignore-->coelacanthe<!--/fr-typo-ignore--> | cœlacanthe |
| <!--fr-typo-ignore-->coeur<!--/fr-typo-ignore-->       | cœur       |
| <!--fr-typo-ignore-->ex aequo<!--/fr-typo-ignore-->    | ex æquo    |
| <!--fr-typo-ignore-->foetus<!--/fr-typo-ignore-->      | fœtus      |
| <!--fr-typo-ignore-->noeud<!--/fr-typo-ignore-->       | nœud       |
| <!--fr-typo-ignore-->oe<!--/fr-typo-ignore-->          | œ          |
| <!--fr-typo-ignore-->oecuménique<!--/fr-typo-ignore--> | œcuménique |
| <!--fr-typo-ignore-->oedeme<!--/fr-typo-ignore-->      | œdème      |


///

/// html | div[style='float: right;width: 50%; text-align: center;']
| Mot         | Correction |
| ----------- | ---------- |
| <!--fr-typo-ignore-->oedipe<!--/fr-typo-ignore-->      | œdipe      |
| <!--fr-typo-ignore-->oeil<!--/fr-typo-ignore-->        | œil        |
| <!--fr-typo-ignore-->oeillet<!--/fr-typo-ignore-->     | œillet     |
| <!--fr-typo-ignore-->oesophage<!--/fr-typo-ignore-->   | œsophage   |
| <!--fr-typo-ignore-->oestrogène<!--/fr-typo-ignore-->  | œstrogène  |
| <!--fr-typo-ignore-->oeuf<!--/fr-typo-ignore-->        | œuf        |
| <!--fr-typo-ignore-->oeuvre<!--/fr-typo-ignore-->      | œuvre      |
| <!--fr-typo-ignore-->oeuvrer<!--/fr-typo-ignore-->     | œuvrer     |
| <!--fr-typo-ignore-->soeur<!--/fr-typo-ignore-->       | sœur       |
| <!--fr-typo-ignore-->tænia<!--/fr-typo-ignore-->       | tænia      |
| <!--fr-typo-ignore-->vitae<!--/fr-typo-ignore-->       | vitæ       |
| <!--fr-typo-ignore-->voeu<!--/fr-typo-ignore-->        | vœu        |
///

/// html | div[style='clear: both;']
///

## Abbréviations

Il n'est pas rare de trouver des abréviations éronnées en français. Par exemple, "M." pour "Monsieur" est correct, mais "Mr." est une abréviation anglaise incorrecte. Le plugin corrige automatiquement certaines abréviations courantes en français. Cela concerne:

- c'est-à-dire (<!--fr-typo-ignore-->c-a-d, c-à-d, c.à-d<!--/fr-typo-ignore--> remplacé par c-a-d)
  - Détection des locutions anglaises (i.e.)
- par exemple (p.ex.)
  - Détection des locutions anglaises (e.g.)
- numéro (n°)
- madame (Mme)
- mademoiselle (Mlle)
- messieurs (MM.)

## Ordinaux

Le plugin remplace les ordinaux incorrects. En bon français on ne dit pas `2ème` mais 2^e^, `3ème` mais 3^e^, `1er` mais 1^er^, `1ère` mais 1^re^. Ceci nécessaite l'utilisation de l'extension Markdown:

```yaml
markdown_extensions:
  - pydownx.caret
```

## Liste

En français on n'utilise pas le caractère `•` pour les listes à puces mais le tiret demi-cadratin `–`. Le plugin remplace automatiquement les puces par des tirets :

- Premier
- Deuxième
- Troisième


## Casse et typographie courante

Les mois, jours, gentilés s'écrivent en minuscule en français. Le plugin corrige ou détecte les erreurs courantes.

La phrase "J'ai mangé Lundi." est incorrecte, par défaut le comportement est d'avertir l'utilisateur :

```text
WARNING -  [fr-typo:casse] index.md: Casse : «Lundi» → «lundi» → «lundi»
```

## Ignorer des sections

Le plugin n'interfère pas avec les blocs de code (délimités par des backticks triples) ni avec le mode mathématique (délimité par `$...$` ou `$$...$$`). Aucune correction n'est appliquée dans ces contextes.

La *front matter* YAML n'est pas non plus modifiée.

Les liens et URL ne sont pas modifiés non plus.

En dehors de ces environnements, il est possible d'ignorer des sections entières en utilisant plusieurs méthodes:

1. Utiliser les balises HTML de commentaire `<!--fr-typo-ignore--> ... <!--/fr-typo-ignore-->` pour entourer la section à ignorer.
2. Utiliser une entrée HTML `<span> ... </span>` pour ignorer une partie d'une ligne.
3. Utiliser l'extension `pymdownx.inlinehilite` et utiliser la syntaxe \`...\`{ .nohilight }.