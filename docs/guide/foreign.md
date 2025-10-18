# Locutions étrangères

Certaines locutions étrangères comme les suivantes doivent -- en français -- être mises en italique:


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

!!! note

    Les locutions latines passées dans les usages comme: à priori, ad hoc, andante, curriculum vitae... ne sont pas corrigées.

Prenons l'exemple de la phrase suivante:

```md
Le chanteur a capella a été diplômé honoris causa par
l'université, il a dit: *Avec cette distinction, je serai de facto plus riche*.
```

Est corrigée en:

> Le chanteur a capella a été diplômé honoris causa par
> l'université, il a dit:
> *Avec cette distinction, je serai de facto plus riche*.
