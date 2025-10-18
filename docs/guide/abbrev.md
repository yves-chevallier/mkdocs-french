# Abbréviations et ordinaux

## Abbréviations

Il n'est pas rare de trouver des abréviations éronnées en français. Par exemple, "M." pour "Monsieur" est correct, mais "Mr." est une abréviation anglaise incorrecte. Le plugin corrige automatiquement certaines abréviations courantes en français. Cela concerne:

- c'est-à-dire (<!--fr-typo-ignore-->==c-a-d==, ==c-à-d==, ==c.à-d==<!--/fr-typo-ignore--> remplacé par ==c-a-d==)
  - Détection des locutions anglaises (==i.e.==)
- par exemple (p.ex.)
  - Détection des locutions anglaises (==e.g.==)
- numéro (==n°==)
- Madame (==Mme==)
- Mademoiselle (==Mlle==)
- Messieurs (==MM.==)
- Confer (==cf.==)

| Locution          | Invalides                      | Correction   |
| ----------------- | ------------------------------ | ------------ |
| C'est-à-dire      | i.e. c.a.d c-a-d, c-à-d, c.à-d | ==c.-à-d.==  |
| Par exemple       | e.g. p.ex. p.ex                | ==p. ex.==   |
| Numéro            | no. num. n°                    | ==n°==       |
| Confer            | c.f.                           | ==cf.==      |
| et collaborateurs | et al.                         | ==et coll.== |

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

| Adjectif  | Avant                               | Après      |
| --------- | ----------------------------------- | ---------- |
| Premier   | <span>1er, 1ier</span>              | ==1^er^==  |
| Première  | <span>1ère, 1iere, 1^ère^</span>    | ==1^re^==  |
| Premières | <span>1ères, 1ieres, 1^ères^</span> | ==1^res^== |
| Deuxième  | <span>2ème, 2ieme, 2^ème^</span>    | ==2^e^==   |
