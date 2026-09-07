# Convention chunk

La grammaire est écrite au format NLTK (`nltk.RegexpParser`), où chaque block `{...}` décrit un motif d'étiquettes POS à regrouper sous une même étiquette de chunk (VP, NP, PP, AP, ADVP, CONJ, PUNCT, NUM, UNKNOWN). Ce document explique, pour chaque règle, le choix fait et la raison de ce choix, sur la base des décisions actées en réunion et des problèmes rencontrés au fil du traitement du corpus.

## 0. Contexte et choix de l'outil

Les analyseurs en constituants existants ne conviennent pas au français ou au projet : Stanza ne propose pas de *consituency parsing* en français, spaCy + benepar ne supporte plus le français, [SEM](https://github.com/YoannDupont/SEM) (Yoann Dupont) produit une segmentation défectueuse (un chunk en contient deux). (19/05, 15/06)

Ainsi nous avons décidé de construire manuellement une grammaire de chunking avec `nltk.RegexpParser`, appliquée sur des séquences `(token, POS)` obtenues via [Stanza](https://stanfordnlp.github.io/stanza/index.html) (choisi face à [spaCy](https://spacy.io/) après comparaison, Stanza étant jugé plus performant et adapté sur le corpus). (19/05)

Une contrainte à assumer dans tous les choix ci-dessous : la simplicité et cohérence avec les conventions déjà posées, en raison de la durée limitée du stage (2 mois). Quand une distinction fine aurait trop complexifié la grammaire, elle a été volontairement abandonnée au profit d'une colonne de métadonnée annexe (ex. négation) ou d'une étiquette générique (`UNKNOWN`). (24/06, 19/06)

La fonction `chunk_type()` ne se contente pasd'appeler le `RegexpPaser` sur les POS bruts : une **chaîne de 7 fonctions de prétraitement** enrichit d'abord la liste `(token, POS)` avec des sous-étiquettes, puis la grammaire est appliquée (détail en §12). Deux garde-fous protègent également la fonction contre les bursts vides ou entièrement `NaN` (cf. §11).

## 1. Etiquettes POS affinées utilisées par la grammaire

La grammaire ne s'appuie pas sur les POS bruts de Stanza mais sur des sous-catégories créées pendant le prétraitement, chacune introduite pour résoudre un problème concret de chunking :

| Etiquette | Origine / Décision | Exemple |
| --- | --- | --- |
| `PRON_cl` | Pronom clitique identifié via `deprel` (`expl:comp`, `expl:pv`) plutôt que par sa seule forme lexicale (la version initiale ne repérait que « y »). Introduit pour que le groupe verbal clitique (*il y a*, *elle se lave*) soit reconnu comme `VP` et non comme `NP` + `VP` séparés. *(Réunion 3 – 09/06, correction 12/06)* | *y*, *se*, *le* (clitique) |
| `ADV_neg` | Séparé de `ADV` pour isoler la négation (*ne*, *pas*, *plus* négatif) et pouvoir, plus tard, déduire une colonne `négation` (0/1) sans complexifier la structure du `VP`. *(24/06, 02/07)* | *ne*, *pas* |
| `ADV_deg` | Séparé de `ADV` pour les adverbes d'intensité/degré (*très*, *plus*, *trop*), utiles à `AP`/`ADVP` mais à ne pas confondre avec `ADV_neg`. *(02/07)* | *très*, *plus* (intensif) |
| `ADV_mwe` / `ADP_mwe` | Renommage de `ADV_fixed`/`ADP_fixed` pour désigner les expressions figées multi-mots (*sans doute*, *de même*, *loin de*). *(Réunion 4 – 18/06)* | *sans doute* |
| `ADP_inf` | Préposition introduisant un infinitif, séparée de `ADP` classique, pour permettre une règle `PP` dédiée aux tournures comme *de travailler*. *(15/06 → 19/06)* | *de* (devant infinitif) |
| `PRON_fixed` | Pronom figé postposé (ex. dans certaines tournures composées), traité comme un ajout optionnel en fin de `VP`. | — |
| `PUNCT_FORT` / `PUNCT_FAIBLE` | Distinction demandée dès le début du projet pour différencier ponctuation forte (`.`, `!`, `?`) et faible (`,`, `;`). *(19/05)* | — |
| `SYM_adp` / `SYM_conj` | Un symbole (`SYM`) reçoit une précision syntaxique **selon sa traduction en langue naturelle** : usage prépositionnel (`/` dans *km/h* = « par ») → `SYM_adp` ; usage conjonctif (`/` dans *et/ou*) → `SYM_conj`. Sans signification claire, le symbole reste `SYM`/`UNKNOWN`. *(Réunion 4 – 18/06, décision détaillée 19/06)* | `/` |
| `NOUN_mwe`, `VERB_inf` | Noms composés et formes infinitives isolées, nécessaires pour les règles `NP` et `VP`/`PP`. | *transport en commun*, *partir* |
| `DET_pre` | Prédéterminant, introduit par `_mark_predeterminer`, placé **avant** un déterminant classique. Distingue *tous* prédéterminant de *tous* pronom, et alimente une règle `NP` dédiée (§3). | *tous*, *toute*, *toutes* (devant un `DET`) |

## 2. `VP` — Groupe verbal

La version initiale du `VP` était plus simple et ne gérait pas correctement les clitiques : un `PRON_cl` isolé était systématiquement absorbé par `NP`, empêchant la reconnaissance du `VP_cl` (*il y a*, *elle se lave*). La règle a donc été retravaillée en plusieurs étapes (12/06, 15/06, 18-19/06) pour aboutir à la version actuelle en 6 règles.

```
    {(<PRON|PRON_cl>?<ADV_neg>*<PRON_cl>?<AUX>+<ADV_neg|ADV|ADV_mwe>*<VERB><PRON_fixed>?<PRON_cl>?)}
    {<PRON|PRON_cl>?<ADV_neg>*<PRON_cl>?<VERB|VERB_inf><ADV_neg|ADV|ADV_mwe>*<VERB|VERB_inf><PRON_cl|PRON_fixed>?}
    {<PRON>?<ADV_neg>*<PRON_cl>*<AUX|VERB><ADV_neg>*<PRON_fixed>?<PRON_cl>?}
    {<PRON|PRON_cl>?<VERB><ADV>*<PRON_cl>?}
    {<AUX|VERB><PRON_cl>?}
    {<VERB_inf>}
```

### Décisions justifiant chaque partie
- **Regroupement global sans distinction interne** : lors de la réunion 5 (24/06), il a été décidé de ranger *tout ce qui constitue un `VP`* (auxiliaire, négation, adverbes, clitiques) dans un seul chunk, sans sous-typage interne (`VP_cl` a été abandonné comme étiquette séparée). La distinction utile pour l'analyse (présence ou non d'une négation) est reportée dans une **colonne `négation` (0/1)** ajoutée après coup, plutôt que dans la structure du chunk.
- **Règle 1 (temps composés)** : gère explicitement l'auxiliaire + participe passé, avec clitiques avant/après, pour capturer des formes comme *elle n'a pas bien marché*.
- **Règle 2 (semi-auxiliaire + infinitif)** : ajoutée après la question posée le 12/06 sur *« … de mesurer … »* et *« pouvoir travailler »* — il a été décidé que la référence à `<VP>` à l'intérieur d'un autre chunk (comme envisagé initialement pour `PP`) posait problème à ce stade du projet, et qu'il valait mieux traiter directement les séquences *verbe/infinitif + verbe/infinitif* comme un seul `VP`.
- **Clitiques multiples (règle 3)** : `<PRON_cl>*` permet d'enchaîner plusieurs pronoms clitiques (*se le*, *le lui*), suite au constat du 22/06 qu'« il peut exister plusieurs pronoms clitiques à la suite ».
- **`il y a` / `il n'y a`** : décision actée en réunion 4 (18/06) — *il y a* forme un seul `VP` (le clitique `y` + l'auxiliaire *a* sont conservés en tokens séparés mais reconnus ensemble grâce à `PRON_cl`) ; en revanche *il n'y a* casse ce regroupement à cause de la négation intercalée, et se découpe en `NP` (*il*) + `ADVP` (*n'*) + `VP` (*y a*).
- **`est-ce`** : ajouté comme cas particulier reconnu en `VP` au niveau du prétraitement (04/09), avec une précaution pour ne pas confondre son sujet inversé avec les autres pronoms sujets (*il*, *elle*...) — traitement repris et systématisé par `_clitique_sujet_postpose` (§12).
- **Infinitif isolé (règle 6)** : conservé comme filet de sécurité pour les infinitifs non rattachés à un semi-auxiliaire (infinitif nominalisé, verbe en tête de proposition).

## 3. `NP` — Groupe nominal
 
```
    {<DET_pre><DET><(NOUN|PRON|PROPN)>+} # tous les ans
    {<(DET|ADV_deg|ADJ|NUM)*>*<(NOUN|NOUN_mwe|PRON|PROPN|PRON_cl)>+<ADJ|NUM>*} # + <NUM><NOUN> -> trente/25 ans
    {<NUM><SYM>} # 90%
    {<DET><ADJ>} # ces derniers...
    {<NP><CCONJ><NP>}
    {<PRON_rel>}
```

### Décisions justifiant chaque partie
- **Règle 1 — prédéterminant (nouveau, `<DET_pre><DET><(NOUN|PRON|PROPN)>+>`)** : ajoutée pour capturer les groupes nominaux introduits par un prédéterminant suivi d'un déterminant classique, type *tous les ans*, *toute la famille*. Auparavant, la règle générale (ci-dessous) traitait déjà *tous* comme un simple `DET` répété dans `<(DET|...)*>*`, ce qui fonctionnait syntaxiquement mais ne distinguait pas le prédéterminant du déterminant. La nouvelle sous-étiquette `DET_pre` (via `_mark_predeterminer`, §12) rend cette distinction explicite.
- **Présence de `PRON_cl` dans la règle générale malgré la décision du 22/06** : la réunion du 22/06 a acté qu'il fallait *retirer `PRON_cl` de `NP`* pour que le `VP` clitique soit prioritaire. Ce principe est respecté par **l'ordre des blocs dans la grammaire** : `VP` est évalué avant `NP` dans la cascade, donc tout `PRON_cl` rattaché à un verbe est déjà consommé par `VP` au moment où `NP` est évalué. Le maintien de `PRON_cl` dans la liste des têtes de `NP` sert uniquement de **filet de sécurité** pour les clitiques orphelins non rattachés à un verbe — cas identifiés comme des fautes d'orthographe (*se* → *ce*, l.3688) ou des clitiques isolés en tête de burst (l.14897).
- **`NUM` dans le `NP`** : correction du 18-19/06 — auparavant, tout `NUM` était systématiquement traité comme faisant partie d'un `NP`. Décision : un `NUM` n'intègre un `NP` que s'il précède un nom/pronom/nom propre (rôle de déterminant : *25 ans*, *trente ans*) ou s'il précède un adjectif (*article 5*). S'il est isolé (*12* seul, l.11654), il reste étiqueté `NUM` (cf. §9).
- **`<NUM><SYM>`** : règle dédiée ajoutée pour les pourcentages (*90 %*), le symbole jouant ici un rôle nominal/adjectival plutôt que d'être classé `UNKNOWN`. *(19/06)*
- **`<DET><ADJ>`** : conserve les tournures elliptiques (*ces derniers…*) en `NP`, après la question soulevée le 20/06 de savoir si ce type de séquence devait plutôt aller dans `AP` — tranchée en faveur de `NP` car l'adjectif y désigne en réalité un référent nominal sous-entendu, pas une simple qualification.
- **Coordination `<NP><CCONJ><NP>`** : ajoutée pour traiter les groupes nominaux coordonnés déjà chunkés à une passe antérieure — complétée par `_mark_postnominal_coord_adj` (§12) pour les cas d'adjectifs coordonnés postposés à l'intérieur d'un même `NP` (*une fille belle et intelligente*).
- **`<PRON_rel>`** : un pronom relatif isolé forme à lui seul un `NP`, pour rester cohérent avec le traitement des autres pronoms.

## 4. `PP` — Groupe prépositionnel
 
```
    {<ADP_inf>+<VERB_inf>+} # "de travailler"
    {<ADP_inf>+<VP>}   # "de pouvoir travailler"
    {<(ADP|ADP_mwe|SYM_adp)>+<(NP|NUM)>?}
```
 
### Décisions justifiant chaque partie
- **Abandon initial de `<ADP>+<VP>` au profit de `<ADP_inf>+<VERB_inf>`, puis réintroduction de `<ADP_inf>+<VP>`** : la toute première version (01/09, avant correction) autorisait un `PP` à contenir un `VP` entier (`{<(ADP|ADP_mwe|SYM_adp)>+<(NP|VP|NUM)>?}`), pour traiter des cas comme *« … de mesurer … »* (question posée le 12/06). Cette formulation posait un problème de dépendance jugé trop lourd entre chunks à l'époque, et avait été remplacée par une règle plus directe : préposition d'infinitif (`ADP_inf`) suivie directement d'un ou plusieurs infinitifs (`<ADP_inf>+<VERB_inf>*`). Cette règle seule ne couvrant pas les périphrases (*de pouvoir travailler*, où *pouvoir travailler* est un `VP` à part entière), la règle `<ADP_inf>+<VP>` a ensuite été **réintroduite** : elle est désormais exploitable sans ambiguïté car, dans le fonctionnement en cascade du `RegexpParser`, le bloc `VP` est résolu **avant** le bloc `PP` — au moment où `PP` est évalué, les `VP` existent déjà comme sous-arbres, et la référence à `<VP>` ne pose donc plus le problème initial.
- **`<ADP_inf>+<VERB_inf>*` devient `<ADP_inf>+<VERB_inf>+`** : le `+` (au lieu du `*`) impose qu'au moins un infinitif suive la préposition d'infinitif ; une préposition d'infinitif seule retombe désormais dans le filet de sécurité de la règle 3.
- **Objet du `PP` rendu optionnel (règle 3 uniquement)** : décision appuyée sur la définition du groupe prépositionnel dans Tellier, Eshkol-Taravella, Dupont & Wang (« Peut-on bien chunker avec de mauvaises étiquettes POS ? », TALN 2014, p. 3) — un `PP` prend une préposition pour tête et est *le plus souvent* suivi d'un groupe nominal ou verbal, mais cela n'est pas obligatoire structurellement. *(19/06)* Cela permet de traiter les prépositions orphelines (burst de révision coupé, préposition en fin de burst) sans créer une catégorie séparée (`PP_brok`/`Unit_brok`, voir §10). Cette souplesse ne s'applique volontairement pas aux règles avec `ADP_inf`, où un infinitif ou un `VP` est requis.
- **`SYM_adp` inclus** : permet de traiter *km/h* où le symbole `/` joue le rôle de la préposition « par » ; la partie *h* du couple *km/h* forme alors avec `/` un `PP`, pendant que *km* (précédé du `NUM`) forme un `NP`. *(18-19/06)*

## 5. `AP` — Groupe adjectival
 
```
    {<(ADV_deg)>*<(ADJ|ADJ_ap)>+} # adv d'intensité
```
 
- Limité à un adverbe de degré éventuel suivi d'un ou plusieurs adjectifs.
- **Question tranchée sur `DET` dans `AP`** : le 20/06, la question a été posée de savoir si des séquences comme *le plus* / *les plus* devaient être traitées en `AP` (le déterminant y jouant un rôle superlatif). Décision actée en réunion 5 (24/06) : `AP` **ne contient pas de `DET`** ; ce type de séquence incomplète (superlatif sans adjectif support, ex. *le plus* en fin de burst de révision) est renvoyé vers `UNKNOWN`, marqué en BILOU comme unité incomplète plutôt que de complexifier la règle `AP`.

## 6. `ADVP` — Groupe adverbial
 
``` 
    {<ADV_deg>+<ADV>}
    {<ADV><CONJ><ADV>}
    {<(ADV|ADV_mwe|INTJ|ADV_neg)>}
```
 
- **Intégration de `ADV_neg`** : permet à une négation isolée (ex. le *n'* de *il n'y a*, une fois le `VP` cassé par la négation, cf. §2) d'être malgré tout rattachée à un chunk plutôt que de rester sans étiquette.
- Les deux premières règles (intensification, coordination par conjonction) restent des cas spécifiques ; la troisième règle est le filet de sécurité général pour tout adverbe, expression adverbiale figée ou interjection isolée.

## 7. `CONJ` — Conjonctions
 
``` 
    {<(CCONJ|SCONJ|SYM_conj)>}
```
 
- **Inclusion de `SYM_conj`** : décision du 18-19/06 de donner une signification syntaxique aux symboles quand cela a du sens en langue naturelle — par exemple *et/ou* où `/` équivaut à « ou », classé `CONJ` plutôt que `UNKNOWN`. La méthode retenue : traduire mentalement le symbole en langue naturelle et vérifier s'il correspond à un usage prépositionnel, nominal ou conjonctif ; en l'absence de correspondance claire, le symbole reste `UNKNOWN` (cf. §10).

## 8. `PUNCT` — Ponctuations
 
```
    {<(PUNCT_FORT|PUNCT_FAIBLE|PUNCT)>} 
```
- Distinction demandée dès le 19/05 pour séparer ponctuation forte et faible dans l'analyse, réunies ici sous un chunk unique `PUNCT` pour ne pas multiplier les catégories de chunk.

## 9. `NUM` — Numéraux isolés
 
```    
    {<NUM>} 
```

- Ajouté en réunion 4 (18/06) après le constat que traiter systématiquement les `NUM` comme `NP` était incorrect pour des cas comme *12* seul (l.11654) ou *« la carte du bus est à 200 »* (l.19246), où le numéral n'est la tête d'aucun groupe nominal.
- Principe retenu : **le `NUM` n'est jamais tête de chunk**. Quand il précède un nom (rôle de déterminant, *25 ans*) il est absorbé par `NP` (§3) ; quand il est seul, sans entourage nominal, il garde l'étiquette `NUM`.
- Les suites de chiffres correspondant à des dates (*09/12/16*) sont volontairement **corrigées en `NUM`** plutôt que laissées en `NOUN` (erreur fréquente de Stanza) : la distinction a été jugée relever de la reconnaissance d'entités nommées (sémantique) et non du POS/chunk (syntaxique), donc hors du périmètre de cette grammaire. *(19/06)*
- Choix de ne pas distinguer les nombres écrits en chiffres de ceux écrits en toutes lettres, faute de temps et de pertinence pour l'objectif de l'étude. *(18/06)*

## 10. `UNKNOWN` — Cas résiduels et unités cassées
 
```
    {<X|SYM|LAS>} # Lettre(s) ajoutée(s) ou supprimée(s)
    {<(ADP|ADP_mwe)>?<DET>} #"de la" = "de là"-> id_19214 + "pour a son sujet"/"contre Jai" (ADP)
```
 
### Évolution de la catégorie
- Une catégorie dédiée `PP_brok` avait d'abord été envisagée (15/06) pour les prépositions « cassées » par des fautes d'orthographe ou des erreurs de POS de Stanza (ex. id_19214 : *de la ou* pour *de là où*). Elle a ensuite été renommée `Unit_brok` (18/06) pour englober plus largement les déterminants seuls et prépositions seules, avec un marquage BILOU pour signaler qu'il manque une suite (probablement dans le burst suivant, après une pause).
- **Décision finale (réunion 5, 24/06)** : abandonner la création d'une étiquette de chunk dédiée (`Unit_brok`) et **tout regrouper dans `UNKNOWN`**, en s'appuyant sur le système BILOU pour indiquer qu'une séquence est incomplète plutôt que d'ajouter une nouvelle catégorie syntaxique qui alourdirait la grammaire — cohérent avec le principe de simplicité retenu pour tout le projet.
- **`<X|SYM|LAS>`** : regroupe les tokens non classifiables (`X`), les symboles sans interprétation syntaxique claire (`SYM` restant, ex. `<m>` jugé être une faute de frappe sans signification récupérable) et les `LAS` (Lettre(s) Ajoutée(s) ou Supprimée(s), notion issue de la grille d'analyse de l'écriture en temps réel d'Amandine Jouvenel, cf. diapositives p. 27-48, réf. du 26/05). Les biais d'homophones fréquents (*es* → 90 % de fautes de révision) ont été rangés ici plutôt que corrigés au cas par cas, faute de méthode fiable pour distinguer automatiquement les rares cas où *es* est un vrai verbe/auxiliaire.
- **`<(ADP|ADP_mwe)>?<DET>`** : traite la confusion entre préposition + déterminant (*de la*) et un adverbe de lieu mal segmenté (*de là*, id_19214), ainsi que les séquences agrammaticales issues d'erreurs de saisie (*pour a son sujet*, *contre Jai*). Plutôt que de risquer un mauvais rattachement à `PP`, ces séquences ambiguës sont neutralisées dans `UNKNOWN`.

## 11. Robustesse et format de sortie de `chunk_type()`
 
- **Garde-fous** ajoutés en tête de la fonction, avant l'appel à la grammaire : retour d'une liste vide si `tagged` est vide, et retour d'une liste vide si **tous** les couples `(mot, tag)` sont vides/`NaN`, pour éviter que le `RegexpParser` ne plante sur des lignes de burst entièrement vides (cas déjà rencontré et corrigé le 03/06 et le 03/07 pour les bursts de type `<PAUSE>`).
- **Format de sortie** : chaque chunk retourné est un triplet `(texte, étiquette, n_slots)`, où `n_slots` correspond au nombre de tokens d'origine ayant composé le chunk — information nécessaire pour réaligner ensuite les chunks avec les bursts (cf. l'« idée de traitement pour chunker sur tout » du 19/06 et du 29/06, qui comparait déjà le nombre de tokens du burst au nombre de « slots » BILOU du chunk).

## 12. Pipeline de prétraitement — ordre et rôle de chaque fonction
 
L'ordre d'appel dans `chunk_type()` n'est pas arbitraire : chaque fonction prépare le terrain pour la suivante ou pour la grammaire elle-même.
 
```python
tagged = _mark_neg_adv(tagged)ed = _mark_degree_adv(tagged)
tagged = _mark_predeterminer(tagged)
tagged = _mark_postnominal_coord_adj(tagged)
tagged = _clitique_sujet_postpose(tagged)
tagged = _pronom_fixed(tagged)
tagged = _mark_infinitive_pp(tagged)
```
 
1. **`_mark_neg_adv`** : repère les adverbes de négation et les retague `ADV_neg`, avant tout autre traitement, car la présence de la négation conditionne la suite de l'analyse (colonne `négation`, cf. décisions du 24/06 et du 02/07).
2. **`_mark_degree_adv`** : repère les adverbes de degré/intensité et les retague `ADV_deg`, utilisés ensuite par `AP`, `ADVP` et la règle `NP` du prédéterminant (cette passe doit précéder la suivante pour ne pas confondre les deux catégories d'adverbes).
3. **`_mark_predeterminer`** *(nouveau)* : identifie les prédéterminants (*tous*, *toute*, *toutes* devant un déterminant) et les retague `DET_pre`, alimentant la règle 1 de `NP` (§3).
4. **`_mark_postnominal_coord_adj`** *(nouveau)* : traite le cas des adjectifs coordonnés postposés au nom (ex. *une fille belle et intelligente*), en assurant que la coordination `ADJ CCONJ ADJ` reste correctement rattachable au `NP` qui précède plutôt que d'être fragmentée entre plusieurs chunks distincts.
5. **`_clitique_sujet_postpose`** *(nouveau)* : traite les cas d'inversion du sujet clitique postposé au verbe (ex. *est-ce*, formes interrogatives avec trait d'union), pour que ce pronom soit bien reconnu comme faisant partie du `VP` plutôt que rattaché à tort à un `NP` suivant — cas évoqué le 04/09 pour *est-ce*.
6. **`_pronom_fixed`** : marque les pronoms figés postposés (`PRON_fixed`), utilisés en fin de règle `VP` (§2).
7. **`_mark_infinitive_pp`** : marque les prépositions introduisant un infinitif (`ADP_inf`), en dernière étape car elle dépend d'un infinitif déjà identifiable (`VERB_inf`) dans la séquence, utilisé par la règle `PP` (§4).
Cet ordre garantit que chaque sous-étiquette est posée sur une séquence déjà stabilisée par les passes précédentes, avant que la grammaire `RegexpParser` ne soit appliquée en une seule fois sur l'ensemble des tokens enrichis.

## 13. Principes transversaux retenus pour l'ensemble de la grammaire
 
1. **Ordre des blocs = priorité de résolution.** Le bloc `VP` est placé avant `NP` et `PP` afin que les clitiques verbaux soient captés avant d'être réinterprétés comme des `NP`, et que `PP` puisse référencer un `VP` déjà construit (*de pouvoir travailler*).
2. **Simplicité avant granularité.** Chaque fois qu'une distinction plus fine aurait nécessité une nouvelle étiquette de chunk (`VP_cl`, `PP_brok`/`Unit_brok`), le choix final a été de la ramener à une catégorie existante (`VP`, `UNKNOWN`) complétée par une colonne de métadonnée (`négation`) ou par le système BILOU, pour rester gérable dans le temps imparti au stage.
3. **Les corrections de biais orthographiques (à/a, ou/où, es/est, sur/sûr…) sont traitées en amont, au niveau du POS**, avant le chunking — la grammaire de chunk elle-même ne fait aucune hypothèse sur ces confusions, elle consomme des POS déjà corrigés (colonnes `pos_stanza` vs `pos_correction`).
4. **Les symboles (`SYM`) sont désambiguïsés par leur traduction en langue naturelle** (prépositionnel, nominal ou conjonctif), et non par une liste figée de symboles autorisés — ce qui explique la création de `SYM_adp`/`SYM_conj` plutôt que le maintien d'un `SYM` unique.
5. **Le `NUM` n'est jamais une tête de chunk** : il est soit absorbé par un `NP` existant (rôle déterminant/adjectival), soit conservé isolé en `NUM`.
6. **Le pipeline de prétraitement (§12) est une extension de ce même principe** : plutôt que de multiplier les cas particuliers directement dans la grammaire `RegexpParser` (peu lisible pour des règles très locales comme le prédéterminant ou le sujet postposé), chaque cas est isolé dans une fonction dédiée qui retague les tokens en amont, laissant la grammaire elle-même aussi simple que possible.