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

## Désactiver les corrections

Le plugin n'interfère pas avec les blocs de code (délimités par des backticks triples) ni avec le mode mathématique. Aucune correction n'est appliquée dans ces contextes. La *front matter* YAML n'est pas non plus modifiée.

En dehors de ces environnements, il est possible d'ignorer des sections entières avec différentes méthodes :

1. Utiliser les balises HTML de commentaire `<!--fr-typo-ignore-->`:

    ```markdown
    <!--fr-typo-ignore-->EVEQUE A PAQUES, etc...<!--/fr-typo-ignore-->
    ```

    > <!--fr-typo-ignore-->EVEQUE A PAQUES, etc...<!--/fr-typo-ignore-->

2. Utiliser une entrée HTML `<span> ... </span>` pour ignorer une partie d'une ligne :

    ```markdown
    <span>EVEQUE A PAQUES, etc...</span>
    ```

    > <span>EVEQUE A PAQUES, etc...</span>

3. Utiliser l'extension `pymdownx.inlinehilite` et utiliser la syntaxe *nohighlight*:

    ```markdown
    `EVEQUE A PAQUES, etc...`{.nohighlight}, EVEQUE A PAQUES, etc...
    ```

    > `EVEQUE A PAQUES, etc...`{.nohighlight}, EVEQUE A PAQUES, etc...

4. Pour les listes à puces, utiliser une classe CSS personnalisée pour désactiver la correction:

    ```markdown
    /// html | div[class='no-french']
    - Premier
    - Deuxième
    - Troisième
    ///
    ```

    > /// html | div[class='no-french']
    > - Premier
    > - Deuxième
    > - Troisième
    > ///
