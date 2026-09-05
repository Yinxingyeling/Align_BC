# Convention chunk

La grammaire est écrite au format NLTK (`nltk.RegexpParser`), où chaque block `{...}` décrit un motif d'étiquettes POS à regrouper sous une même étiquette de chunk (VP, NP, PP, AP, ADVP, CONJ, PUNCT, NUM, UNKNOWN).

Principes généraux 
-

A l'intérieur d'un même chunk, les règles sont testés dans l'ordre d'écriture. La première règles qui correspond à une séquence de tokens l'emporte, les règles suivantes ne s'appliquent qu'aux tokens non déjà capturés.

| Notations | Description | 
| --- | --- |
| \<TAG> | un token portant exactement cette étiquette. |
| \<TAG1\|TAG2> | disjonction, un token portant l'une ou l'autre étiquette. |
| \<TAG>* | zéro, une ou plusieurs occurrences. |
| \<TAG>+ | une ou plusieurs occurrences. |
| \<TAG>? | zéro ou une occurrence (optionnel). |
| \<(TAG1\|TAG2)\*>* | groupe capturant une disjonction répétée. |

Les catégories syntaxiques sont représentées entre chevrons :

* \<PRON> : pronom ;
* \<DET> : déterminant ;
* \<NOUN> : nom ;
* \<PROPN> : nom propre ;
* \<ADJ> : adjectif ;
* \<ADV> : adverbe ;
* \<VERB> : verbe ;
* \<AUX> : auxiliaire ;
* \<ADP> : adposition/préposition ;
* \<NUM> : nombre ;
* \<PUNCT> : ponctuation ;
* \<CCONJ> : conjonction de coordination ;
* \<SCONJ> : conjonction de subordination.

Les catégories spécialisées suivent la même convention. Par exemple :

* \<PRON_cl> : pronom clitique ;
* \<PRON_fixed> : pronom à position fixe ;
* \<VERB_inf> : verbe à l’infinitif ;
* \<ADV_neg> : adverbe de négation ;
* \<ADV_deg> : adverbe de degré/intensité ;
* \<ADV_mwe> : adverbe appartenant à une expression polylexicale ;
* \<ADP_inf> : préposition introduisant un infinitif ;
* \<ADP_mwe> : adposition polylexicale ;
* \<SYM_adp> : symbole utilisé comme adposition.
* \<DET_pre> : prédéterminant

## Étiquettes chunks

| Tag | Description |
| --- | --- | 
| `VP` | Groupe verbal |
| `NP` | Groupe nominal |
| `PP` | Groupe prépositionnel |
| `AP` | Groupe adjectival |
| `ADVP` | Groupe adverbial |
| `CONJ` | Conjonction |
| `PUNCT` | Ponctuation |
| `NUM` | Numéral isolé, sans rôle nominal |
| `UNKNOWN` | Chunk non résolu (symbole isolé, unité cassée, séquence ambiguë, lettres ajoutées ou supprimées (LAS)) | 
| `<PAUSE>`, `<SUPPR>`, `<SPACE>` | Étiquette marquant une ligne de suppression, d'espace ou encore une pause ajoutée manuellement pour distinguer les bursts |

## Listes des expressions figées

Chemin dans l'arbre
```bash
Align_BC/src/ressources/
```

## Précisions et exemples
### VP — Groupe verbal

Le chunk `VP` correspond à un **groupe verbal**. Trois configurations sont distinguées : les temps composés, les constructions avec semi-auxiliaire et infinitif, et les temps simples.

| Règle | Description | Exemple |
|---|---|---|
| 1. Temps composés | auxiliaire (+ négation/adverbes) + participe passé | `vous [VP 0] n' [VP 1] avez [VP 2] pas [VP 3] vu [VP 4]` |
| 2. Semi-auxiliaire + infinitif | verbe conjugué + infinitif | `je [VP 0] vais [VP 1] passer [VP 2]` |
| 3. Temps simples + clitiques | plusieurs clitiques réunis dans le même chunk | `il [VP 0] y [VP 1] a [VP 2]` <br>  `est [VP 0] -ce [VP 1]` |
| 4. Verbe + adverbe postposé | verbe simple suivi d'un adverbe | `il [VP 0] parle [VP 1] rapidement [VP 2]` |
| 5. Filet de sécurité | auxiliaire/verbe isolé | `est [VP 0]` |
| 6. Infinitif isolé | infinitif non rattaché à un semi-auxiliaire | `prendre [VP 0]` |

### NP — Groupe nominal
 
| Règle | Description | Exemple |
|---|---|---|
| 1. Prédéterminant + déterminant | *tous/toute(s)* + `DET` + nom | `tous [NP 0] les [NP 1] ans [NP 2]` |
| 2. Groupe nominal standard | déterminant(s)/adjectif(s)/numéral(aux) + tête nominale + adjectif(s)/numéral(aux) postposé(s) | `les [NP 0] trente [NP 1] derniers [NP 2] ans [NP 3]` |
| 3. Numéral + symbole | pourcentages, unités | `90 [NP 0] % [NP 1]` |
| 4. Déterminant + adjectif elliptique | nom sous-entendu | `ces [NP 0] derniers [NP 1]` |
| 6. Pronom relatif isolé | forme à lui seul un `NP` | `qui [NP 0]` |

### PP — Groupe prépositionnel
 
Une préposition reste tête de chunk même sans complément (pour couvrir les prépositions orphelines en fin de burst).
 
| Règle | Description | Exemple |
|---|---|---|
| 1. Préposition d'infinitif + infinitif | *de*, *à* + infinitif | `de [PP 0] travailler [PP 1]` |
| 2. Préposition d'infinitif + périphrase verbale | préposition + `VP` (semi-auxiliaire + infinitif) | `de [PP 0] pouvoir travailler [PP 1-2]` |
| 3. Préposition + complément optionnel | préposition simple/composée/symbolique + `NP`/`NUM` (ou rien) | `sur [PP 0] les [PP 1] paquets [PP 2]` |

### AP — Groupe adjectival
 
| Règle | Description | Exemple |
|---|---|---|
| 1. Adverbe de degré + adjectif(s) | intensité + adjectif | `très [AP 0] intéressant [AP 1]` |
| 2. Adjectif | adjectif seul | `correctes [AP 0]` | 
 
> `AP` ne contient jamais de déterminant : *le plus* (sans adjectif support) n'est pas un `AP`, il reste `ADVP`.

### ADVP — Groupe adverbial
 
| Règle | Description | Exemple |
|---|---|---|
| 1. Intensification | adverbe de degré + adverbe | `trop [ADVP 0] peu [ADVP 1]` |
| 2. Coordination | adverbe + conjonction + adverbe | `plus [ADVP 0] ni [CONJ] moins [ADVP 1]` |
| 3. Filet de sécurité | adverbe, interjection ou négation isolée | `déjà [ADVP 0]` |

### CONJ — Conjonctions
 
| Règle | Description | Exemple |
|---|---|---|
| 1. Coordination / subordination / symbole conjonctif | `CCONJ`, `SCONJ` ou `SYM_conj` | `et [CONJ 0]`, `/ [CONJ 0]` *(dans "et/ou")* |

### PUNCT — Ponctuations
 
| Règle | Description | Exemple |
|---|---|---|
| 1. Ponctuation forte, faible ou générique | `.`, `!`, `?`, `,`, `;` | `. [PUNCT 0]` |

### NUM — Numéral isolé
 
| Règle | Description | Exemple |
|---|---|---|
| 1. Numéral sans rôle nominal | chiffre seul, sans nom/symbole autour | `12 [NUM 0]` |

### UNKNOWN — Cas résiduels
 
| Règle | Description | Exemple |
|---|---|---|
| 1. Symbole/lettre non résolu | `X`, `SYM` sans sens syntaxique, `LAS` | `<m> [UNKNOWN 0]` |

> Tout ce qui n'a pas pu être reconnu par `RegexpParser` est étiqueté ainsi.

### Rappel des points sensibles
 
- **Ordre d'application** : `VP` est résolu avant `PP`, ce qui permet à `PP` de référencer un `VP` déjà construit (*de pouvoir travailler*).
- **Répétition de clitiques** : toujours réunie dans un seul chunk `VP` (*on se on constate*), jamais scindée.
- **Le clitique n'est jamais tête de chunk** : `PRON_cl` sert de filet de sécurité dans `NP` uniquement pour les clitiques orphelins (faute d'orthographe, clitique isolé), pas pour ceux déjà absorbés par un `VP`.
- **Numéral jamais tête** : `NUM` intègre un `NP` s'il précède un nom/adjectif, sinon il reste `NUM` seul.