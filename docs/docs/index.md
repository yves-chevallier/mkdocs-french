# MkDocs French Plugin

Ce plugin MkDocs améliore la typographie française et corrige automatiquement certaines erreurs courantes dans les documents Markdown. L'ouvrage de référence utilisé pour les conventions typographiques en français est [Petites leçons de typographie](https://jacques-andre.fr/faqtypo/lessons.pdf) de Jacques André.

Ce plugin est largement configurable, chaque règle peut être activée ou désactivée, et le comportement peut être ajusté pour corriger automatiquement les erreurs (`fix`), émettre un avertissement (`warn`) ou ignorer la règle (`ignore`).

Les règles traitées sont :

- Corrections de ponctuation (espaces insécables, guillemets, apostrophes, points de suspension, etc.)
- Diacritiques manquants sur les mots en majuscules (<span>ECOLE</span> → ÉCOLE)
- Locutions étrangères en italique (a capella, de facto, etc.)
- Ligatures typographiques courantes (œ dans coeur, oeuvre, etc.)
- Abréviations courantes (M., Mme, p.ex., n°, etc.)
- Ordinaux (<span>1er</span> → 1^er^)
- Unités (espaces insécables entre nombres et unités comme 100km)
- Listes à puces (remplacement de `•` par `–`)
- Casse et typographie courante (jours, mois, gentilés en minuscule)
- Traduction des admonitions standard (warning → Avertissement, etc.)

## Espacement et ponctuation

En français, les ponctuations doubles sont précédées d'une espace insécable U+202F. Markdown ne le gère pas nativement. Si l'éditeur ajoute manuellement une espace comme dans `ceci :`, le risque est que le rendu HTML puisse ajouter une césure de ligne entre le mot et la ponctuation. Inversément, si l'éditeur n'ajoute pas d'espace, le rendu n'est pas correct.

Le plugin ajoute automatiquement une espace insécable U+202F avant les ponctuations doubles: `; ! ?` et une espace fine inssécable U+00A0 avant les deux-points `:`.

Les points de suspension `...` sont remplacés par le caractère Unicode U+2026 `…`.

Les guillemets français `« »` sont également gérés. Le plugin ajoute une espace insécable après le guillemet ouvrant et avant le guillemet fermant. Il remplacera également les guillemets droits `"` par des guillemets français.

L'apostrophe droite `'` U+0027 est remplacée par l'apostrophe typographique U+2019 `’` pour l'élision comme dans "l'homme" ou "aujourd'hui". Ceci permet la selection correcte du mot dans certains navigateurs et garantit l'absence de césure.

Correction des contractions avec la virgule et le point :

| Incorrect | Correct |
| --------- | ------- |
| ?.        | ?       |
| !.        | !       |
| etc..     | etc.    |
| etc...    | etc.    |
| etc....   | etc.    |
| m, ...    | m...    |

!!! info

    Les URL comme http:// ou mailto:// ne sont pas modifiées.

La configuration s'effectue ainsi:

```yaml
plugins:
  - french:
      punctuation: fix # ou warn ou ignore
```

## Diacritiques

Le plugin détecte également les diacritiques manquants sur des mots écrits en majuscules. Par exemple `ECOLE` devient `ÉCOLE` et `CA` devient `ÇA`.

La correction s'appuie sur le dictionnaire Lexique383 (téléchargé et mis en cache au premier usage) qui répertorie les formes accentuées les plus fréquentes. Activez-la ainsi :

```yaml
plugins:
  - french:
      diacritics: fix # ou warn ou ignore
```

En mode `warn`, un message est émis sans modifier le texte d'origine. Les mots ambigus (plusieurs formes accentuées possibles) sont volontairement laissés tels quels.

!!! info

    Le fichier Lexique est téléchargé automatiquement et mis en cache;
    en cas d'environnement sans accès réseau, un jeu de secours réduit est utilisé.

## Locutions étrangères

Certaines locutions étrangères comme les suivantes doivent, en français être en italique:

- a capella,
- de facto,
- honoris causa,
- ipso facto,
- manu militari,
- sine die.

Le plugin corrige automatiquement ces locutions. La configuration s'effectue ainsi:

```yaml
plugins:
  - french:
      foreign: fix # ou warn ou ignore
```

Notons que les locutions latines passées dans les usages comme à priori, ad hoc, andante, curriculum vitae... ne sont pas corrigées.

## Ligatures

Le plugin remplace automatiquement certaines combinaisons de lettres par des ligatures typographiques courantes en français. Par exemple, "oe" est remplacé par "œ" dans des mots comme "coeur", "oeuvre", "boeuf", "oeil", "oeuf", "oesophage" ou "coelacanthe". Voici la liste complète des mots concernés:

/// html | div[style='float: left; width: 50%; text-align: center;']


| Mot                                                    | Correction |
| ------------------------------------------------------ | ---------- |
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
| Mot                                                   | Correction |
| ----------------------------------------------------- | ---------- |
| <!--fr-typo-ignore-->oedipe<!--/fr-typo-ignore-->     | œdipe      |
| <!--fr-typo-ignore-->oeil<!--/fr-typo-ignore-->       | œil        |
| <!--fr-typo-ignore-->oeillet<!--/fr-typo-ignore-->    | œillet     |
| <!--fr-typo-ignore-->oesophage<!--/fr-typo-ignore-->  | œsophage   |
| <!--fr-typo-ignore-->oestrogène<!--/fr-typo-ignore--> | œstrogène  |
| <!--fr-typo-ignore-->oeuf<!--/fr-typo-ignore-->       | œuf        |
| <!--fr-typo-ignore-->oeuvre<!--/fr-typo-ignore-->     | œuvre      |
| <!--fr-typo-ignore-->oeuvrer<!--/fr-typo-ignore-->    | œuvrer     |
| <!--fr-typo-ignore-->soeur<!--/fr-typo-ignore-->      | sœur       |
| <!--fr-typo-ignore-->vitae<!--/fr-typo-ignore-->      | vitæ       |
| <!--fr-typo-ignore-->voeu<!--/fr-typo-ignore-->       | vœu        |
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
- Madame (Mme)
- Mademoiselle (Mlle)
- Messieurs (MM.)
- Confer (cf.)

| Locution          | Invalides                      | Correction |
| ----------------- | ------------------------------ | ---------- |
| C'est-à-dire      | i.e. c.a.d c-a-d, c-à-d, c.à-d | c.-à-d.    |
| Par exemple       | e.g. p.ex. p.ex                | p. ex.     |
| Numéro            | no. num. n°                    | n°         |
| Confer            | c.f.                           | cf.        |
| et collaborateurs | et al.                         | et coll.   |

## Ordinaux

Le plugin remplace les ordinaux incorrects. En bon français on ne dit pas <span>2ème</span> mais 2^e^, <span>3ème</span> mais 3^e^, <span>1er</span> mais 1^er^, <span>1ère</span> mais 1^re^. Ceci nécessaite l'utilisation de l'extension Markdown:

```yaml
markdown_extensions:
  - pydownx.caret
```

La configuration s'effectue ainsi:

```yaml
plugins:
  - french:
      ordinaux: fix # ou warn ou ignore
```

| Adjectif  | Avant                               | Après  |
| --------- | ----------------------------------- | ------ |
| Premier   | <span>1er, 1ier</span>              | 1^er^  |
| Première  | <span>1ère, 1iere, 1^ère^</span>    | 1^re^  |
| Premières | <span>1ères, 1ieres, 1^ères^</span> | 1^res^ |
| Deuxième  | <span>2ème, 2ieme, 2^ème^</span>    | 2^e^   |

## Unités

Le plugin ajoute une espace insécable (U+202F) entre les nombres et les unités courantes comme `kg`, `cm`, `m`, `km`, `g`, `L`, `h`, `min`, `s` et les symboles monétaires comme `€`, `$`, `£`, `¥`.

Par exemple `100km` est corrigé en `100 km`. Si vous souhaitez conserver la forme originale, entourez la valeur d'un élément ignoré (`<span>100km</span>` par exemple).

La configuration s'effectue ainsi:

```yaml
plugins:
  - french:
      units: fix # ou warn ou ignore
```

## Liste

En français on n'utilise pas le caractère `•` pour les listes à puces mais le tiret demi-cadratin `–`. Le plugin remplace automatiquement les puces par des tirets :

- Premier
- Deuxième
- Troisième

Cette correction est configurable et peut être désactivée :

```yaml
plugins:
  - french:
      enable_css_bullets: false
```

## Casse et typographie courante

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

## Admonitions

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

!!! pied-piper

    Cause toujours tu m'intéresses !

## Désactiver les corrections

Le plugin n'interfère pas avec les blocs de code (délimités par des backticks triples) ni avec le mode mathématique. Aucune correction n'est appliquée dans ces contextes. La *front matter* YAML n'est pas non plus modifiée.

En dehors de ces environnements, il est possible d'ignorer des sections entières avec différentes méthodes :

1. Utiliser les balises HTML de commentaire `<!--fr-typo-ignore-->`:

    ```markdown
    En français, on n'écrit pas
    "<!--fr-typo-ignore-->LE CONGRES<!--/fr-typo-ignore-->" mais
    "LE CONGRÈS" si c'est un salon ou "LE CONGRES" si c'est un poisson.
    ```

2. Utiliser une entrée HTML `<span> ... </span>` pour ignorer une partie d'une ligne :

    ```markdown
    Écrire <span>2ème</span> est incorrect en français, on écrit 2^e^.
    ```

3. Utiliser l'extension `pymdownx.inlinehilite` et utiliser la syntaxe *nohighlight*:

    ```markdown
    Cette section `n'est pas corrigée`{.nohighlight}.
    ```
