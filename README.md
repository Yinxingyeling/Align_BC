# Align_BC
Projet de recherche (stage Clesthia) : alignement des phases de production des données d'écriture enregistrées (**burst**) et les **chunks**.

## Présentation
**But de l'analyse**

L'objectif de cette recherche est d'étudier l'alignement entre les **bursts** (segments de frappe délimités par une pause dans l'écriture enregistré) et les **chunks** (groupes syntaxiques). La question centrale est la suivante : 
> Les frontières des bursts correspondent-elles aux frontières des chunks ?

Le projet fournit une chaîne de traitement pour :
1. Lire un corpus de bursts d'écriture (CSV, Excel ou JSON);
2. Tokeniser et annoter morphosyntaxiquement (POS) chaque burst avec [Stanza](https://stanfordnlp.github.io/stanza/);
3. Regrouper les tokens en chunks syntaxiques (NP, VP, PP, AP, ADVP, CONJ, PUNCT, NUM, UNKNOWN) avec des étiquettes BILOU;
4. Filtrer et exporter les résultats

## Structure du dépôt
```text
Align_BC/
├── data/
│   ├── corpus/     # corpus bruts (formulation, planification, révision)
│   ├── postag/     # corpus annotés en POS (csv, xlsx, json)
│   └── chunks/     # corpus chunkés avec étiquettes BILOU (csv, xlsx, json)
├── src/
│   ├── main_tok_chunk.py   # CLI principale : process / filter / chunk
│   ├── read_write.py       # lecture, conversion et export des corpus
│   ├── tok_pos.py          # tokenisation et POS tagging (Stanza)
│   ├── chunker_fr.py       # chunking syntaxique et étiquettes BILOU (NLTK)
│   └── ressources/         # listes d'adverbes/adpositions figés
└── README.md
```

## Installation
```bash
git clone https://github.com/Yinxingyeling/Align_BC.git
cd Align_BC
pip install -r requirements.txt
```
`openpyxl` est nécessaire pour lire/écrire des fichiers Excel (`.xlsx`)

Au premier lancement, télécharger le modèle français de Stanza (si ce n'est pas déjà fait) :
```python
import stanza
stanza.download("fr")
```

## Utilisation 
Toute la chaîne de traitement est pilotée depuis `src/main_tok_chunk.py`, qui propose trois commandes : `process`, `filter` et `chunk`.

### `process` -- lecture, POS tagging et chunking

A noter que pour le traitement chunk, il est obligatoire de passer par le POS tagging, car le traitement s'aide du chunker de NLTK qui se base sur les POS tagging. <br>
Si le corpus utilisé est déjà postagger, lancer simplement avec `-c`, sinon passer par `-p`.
```bash
# Tokeniser et annoter en POS un dossier de corpus {CSV, Excel, JSON}
python src/main_tok_chunk.py process data/corpus/ -p

# Idem avec chunking
python src/main_tok_chunk.py process data/corpus/ -p -c

# Exporter le résultat en JSON
python src/main_tok_chunk.py process data/corpus/ -p -c -o data/results.json -f json

# Lire un corpus déjà traité (JSON) sous forme de DataFrame ou dict
python src/main_tok_chunk.py process data/results.json --json-reader dict
```

Option principales : 
| Option | Description |
| --- | --- | 
| `-p`, `--postagger` | Tokenisation + POS tagging |
| `-c`, `--chunker` |  Chunking syntaxique  | 
| `-o`, `--outputgile FILE` | fichier de sortie | 
| `-f`, `--format {json,excel,csv}` | Format to save |
| `--json-reader {df,dict}` | To read json file | 
| `--column COLUMN [COLUMN ...]` | Limit which columns were used |
| `--limit LIMIT` | Limit lines to process. Give a number | 
| `--is-tagged`, `--no-is-tagged`| True if is postagged | 
| `--is-chunked`, `--no-is-chunked` | True if is chunked | 

### `filter` -- filtrage du corpus
```bash
# Filtrer sur plusieurs catégories POS
python src/main_tok_chunk.py filter data/results.csv --columns2filter pos_correction --items2filter VERB AUX

# Lister les valeurs disponibles pour chaque colonne filtrable
python src/main_tok_chunk.py filter data/results.csv --filter-helper
```
Colonnes filtrables : `input_corpus`, `charge`, `pos_stanza`, `pos_correction`, `type_chunk`, `negation`, `bilou`, `categ`.

## Formats d'entrée/sortie
* Entrées : fichiers .csv, .xlsx, .json, ou dossier contenant plusieurs fichiers CSV/Excel.
* Sorties : affichage terminal, ou export CSV / Excel / JSON.

## Données
Le dossier `data/` contient :
* `corpus/` : corpus bruts par phase d'écriture (formulation, planification, révision) ;
* `postag/` : corpus annotés en POS ;
* `chunks/` : corpus finaux avec chunking et étiquettes BILOU.

## Information et Licence
Information 
-
Stage réalisé dans le cadre du projet [Pro-TEXT](https://pro-text.huma-num.fr/).

> Bouriga, S., & Olive, T. (2020). The Pro-TEXT French Adult Sub-corpus of keystroke logs and final texts. Pro-TEXT: Le processus de textualisation. <br> https://pro-text.huma-num.fr/ressources/

Licence
-
> Licence & access — Freely available under CC BY 4.0, except the Professional Sub-corpus (sensitive data, upon request only). <br> Contact: georgeta.cislaru@sorbonne-nouvelle.fr