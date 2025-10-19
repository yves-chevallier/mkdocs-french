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
