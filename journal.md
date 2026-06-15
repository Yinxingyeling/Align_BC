# Journal du stage
> Stage Clesthia sous la tutelle de Mme Cislaru et Mme Eshkol-Taravella
>
> Date : 13/05/2026 - 13/07/2026 

## Réunion - 1 (13/05)

* Réunion : mise en place et orientation du projet
    - explication des données à traiter

## Données (15/05)

* Reprise des anciennes données du projet (ce que les anciens stagiaires ont fait)
* Début d'une démarche

## Test et reproduction (19/05)
### Tokenisation, lemmatisation, postagging
* Tester différents modules : `stanza`, `spacy`
    |           | Stanza    | spaCy |
    | --        | --        | --    |
    | “du”      | ADP + DET | ADP   |
    | “space”   | skip      | SPACE |
    | emp	    | X	        | NUM   |
    | êcheur	| VERB	    | VERB  |
    | égalemn	| ADV	    | ADJ   |
    | ent	    | ADV	    | ADV   |
    | e	        | ADP	    | NOUN  |

* Utilisation de nltk et treetagger pour la tokenisation
$\rightarrow$ impossible de télécharger le corpus français dans la base de données de treetagger.

### Chunking
* `stanza` : *constituency* ne supporte pas le français ❌
* `nltk` : doit construire manuellement les règles
* `spacy` + `benepar` : *benepar* ne supporte pas le français

#### Autres proppositions 
* `stanza` : *depparse* $\rightarrow$ reconstruction avec les syntaxes de dépendance
* `spacy` : *noun_chunks* (chunking seulement pour les NP)
* reprendre [SEM](https://github.com/YoannDupont/SEM) de Yoann Dupont

### Problèmes dans les données

* Les résultats finaux de PAD (`PAD/data/fichier_json`) sont en partie désordonnées
    |	            |	| Corpus A	                        | Corpus B                          |
    | ------------- | - | --------------------------------  | --------------------------------  |
    |Formulation	| +	| arrêt tabac…	                    | **cadre médecine traditionnelle** |
    |	            | -	| législation France…	            | **cadre médecine traditionnelle** |
    |Plannification	| +	| **cadre médecine traditionnelle**	| **cadre médecine traditionnelle** |
    |	            | -	| Nous venons app…	                | Nous venons app…                  |
    |Révision	    | +	| Pour diminuer	                    | Pour diminuer                     |
    |	            | -	| Question législation	            | Question législation              |

    Corpus A = burst | Corpus B = chunk
    $\rightarrow$ Le problème ne vient pas des scripts mais des fichiers d'entrée $\Rightarrow$ les fichiers ont été confondu

## SEM (20/05)

### `filesFromFolder` 
Permet d'extraire les fichiers d'un dossier. La fonction rend un dictionnaire avec pour clé l'extension et la valeur une liste des chemins des fichiers

### `csv2txt`
Fonction de prétraitement avant l'utilisation de SEM. Il transforme les données **burst** du csv ou excel en texte brut

### SEM
Problèmes rencontrés lors de l'installation et l'utilisation
* Il ne marche qu'avec un **python <= python=3.8**
* python ne supporte plus `cgi`, il faut changer en `html` et l'importer dans le fichier *html.py*
    $\rightarrow$ cette manipulation est obligatoire si et seulement si nous voulons une sortie en html

Commandes utilisées :
-
Ces commandes doiven être faites dans le dossier SEM
```bash
# Après création de l'environnement : python=3.8
rm -rf build dist *.egg-info sem_data
python -m pip install setuptools wheel
python -m ensurepip --upgrade
python -m pip install --upgrade pip setuptools wheel
python setup.py install
sem --help # vérifier si SEM marche bien

# Run SEM in SEM repo
sem tagger resources/master/fr/chunking.xml ../Align_BC/data/txt/revision-.txt -o ../Align_BC/data/html/ -f html
sem tagger resources/master/fr/chunking.xml ../Align_BC/data/txt/formulation-.txt -o ../Align_BC/data/html/ -f html
sem tagger resources/master/fr/chunking.xml ../Align_BC/data/txt/planification-.txt -o ../Align_BC/data/html/ -f html
```

## Réunion - 2 (21/05)
* Fichier de sortie : peut réunir tout, il faut juste qu'on puisse faire les comparaisons par la suite (ajout d'un filtrage si nous réunissons tout)
* Garder toutes les colonnes du corpus d'origine et ajouter les traitements (chunk et pos) $\rightarrow$ ranger par token donc doublé les autres informations déjà présentes

### Résultat attendu (CSV et JSON)
#### CSV
![résultat attendu en csv](img/csv_result.png)
* ajout d'une ligne vide avec le symbole **&** pour montrer une pause
* les lignes "vides" (comportant des espaces ou suppression) sont gardé car ils ont des données implicites que nous retrouvons dans *charBurst*

#### JSON
```json
{ id_0 : {
			information : { "ID" : "F+S1",
                            "input_corpus" : "Formulation",
                            "charge" : "+",
                            "outil" : "TW",
                            "n_burst" : int,
                            ... }
			burst : "L'arrêt du tabac est",
			token : ["l", "arrêt", "du", "tabac", "est"],
			lem : [...], # peut être ignoré
			POS : [("l", DET), ()], # POS précis
			Pause : 0/1, #int
			Bust_categ : "", #str
			Chunk : [("L'arrêt", BL, NP),()] # sous forme de liste 

...}
```
* Dans les chunk, réunir les informations sur chunk et chunkCateg du csv pour avoir les informations du **O** pour les pauses ou les lignes vides
* On peut ajouter les données des autres colonnes

<div style="border:5px solid powderblue; ">
<span style="padding:1px; color:red; background-color:lightgrey; margin:5px"><b>Note :</b></span><br>
<div style="margin-left:15px">
B - 'beggining' 
I - 'inside' <br>
L - 'last' <br>
O - 'outside' <br>
U - 'unit' <br>
----------------- <br>
NP - 'nominal' <br>
VP - 'verbal' <br>
PP - 'preposition' <br>
GADJ - 'adjectif' <br>
GADV - 'adverbe' <br>
CONJC - 'conjonction' <br>
</div>
</div>

### Choix des modules de chunking et postagging
* SEM a un problème dans le chunking : certaines segmentations sont erronées, dans un chunk, nous retrouvons deux chunks
![Résultat du chunking par SEM au format HTML](img/chunking_sem.png)
* Choix du module de chunking : NLTK
    - Les chunks étant erronés, et ne connaissant pas d'autres modules de chunking performants pour le français, nous avons décidé de construire manuellement un chunker via le module `nltk`, où le chunker marche avec les règles que nous donnons.
* Choix du module de postagging :
    |           | Stanza    | spaCy | Description |
    | --        | --        | --    | --          |
    | “du”      | ADP + DET | ADP   | stanza divide en "de+le" |
    | “space”   | skip      | SPACE | ignoré par stanza |
    | emp	    | X	        | NUM   | token du burst 1 : stanza reconnaît pour unknow, alors que spacy = number
    | êcher	| VERB	    | VERB  | token du burst 2 $\Rightarrow$ *empêcher* |
    | égalemn	| ADV	    | ADJ   | token du burst 1 : stanza = ADV ☑️ |alors que spacy = ADJ ❌ |
    | ent	    | ADV	    | ADV   | token du burst 2 $\Rightarrow$ *également* |
    | e	        | ADP	    | NOUN  | souvent une révision : oublie des terminaison (e/s/es...) |

    - Après un test rapide entre `stanza` et `spacy`, nous pouvons voir que `stanza` est plus performant et pour la plupart des tokens, plus adapté pour notre corpus et le français. Ainsi, nous avons choisi de prendre le module `stanza` pour l'étiquetages de nos tokens.

#### Amélioration
* *emp* + *êcher* que `stanza` étiquète **X+VERB** $\rightarrow$ changer par **VERB-1** et **VERB-2** pour avoir la liaison entre les deux.
    - La segmentation est ainsi car ce sont deux burst différents, **Hypothèse 1** : une pause ici pour trouver la touche avec le **^** sur le clavier ? $\rightarrow$ vérifier l'hypothèse avec la durée de pause
* *du* : garder l'étiquetage de spaCy qui semble être plus adapté pour notre cas, car l'automatisation est plus simple à faire et ainsi, nous avons qu'une seule ligne pour *du* et non *de+la* (sortie de `stanza`)
    - il faut donc regrouper tous les dispatch de `stanza` et changer l'étiquette en ADP $\Rightarrow$ *du* = **ADP**
* Créer un ou deux autres tags pour les burst qui *e*, *es*, *s*, *ees* qui sont souvents des oublies ou des corrections d'erreurs de terminaison du genre ou du nombre. Souvent présent pour les NC ou ADJ
* Ignorer les espaces dans le postagging, mais garder le vide dans la sortie finale

### Améliorations globales
* Ajouter un filtrage des données pour une meilleur comparaison des données par la suite (facilite l'analyse)
* Ajouter une catégories de POS et de chunk pour les ponctuations et préciser si c'est une ponctuation forte ou faible.
    - `punct_forte = [",", ";", ":"]`
    - `punct_faible = [".", "!", "?"]`

### Ouverture
* Pour le postagging, nous pouvons détailler (genre, nombre...), ce sont des données qui permettent une analyse plus fine et de répondre à des hypothèses avec plus de précision.
* Prendre en compte l'entourage de *du* pour avoir des POS adaptés aux différentes situation (différencier ADP+DET et DET)
* `stanza` saute toutes les espaces, or certains espaces comprtent des données cachées qui ne sont pas explicités dans les *burst* (ce dont nos analyses portent dans ce projet), mais dans les *burstChar*. Ainsi, trouver un moyen de prendre en compte ces données implicites pour avoir plus de données d'analyse.

## Rédaction du journal et postagging avec stanza (22/05)
* Mise au propre du journal de bord et rédaction des décisions prises lors de la réunion 2. 
    - Ajout des quelques détails pour une meilleur compréhension du journal pour les camarades suivants.
* Finaliser le script de postagging avec `stanza` en ajoutant les modifications mentionnées lors de la réunion 2.

## Postagging avec stanza - 2 (26/05)
- Vérification des tests à ajouté pour un POS plus précis et adapté au corpus.
- LAS (selon la diapo *Analyse des données d’écriture en temps réel* — Amandine Jouvenel) voir diapo p. 27-48.
- Utilisation de `explode` dans pandas : range chaque élément de la liste en un élément par ligne tout en répliquant les données des autres colonnes

Problème :
- sur Linux, le GPU n’est pas activé, il faut installer la carte NVIDIA et redémarrer l’ordinateur

## Postagging avec stanza - 3 (27/05)
* Définir les tokens à tagger LAS 
* Détaillé le tag pour les ponctuations 
    * punct_fort = [".", "!", "?"]
    * punct_faible = [",", ";", ":"]

## Postagging avec stanza - 4 (28/05)
- Correction automatique pour les pos=X, si en collant le text A et le text B (A token mtn, B token suivant), leur POS est le même que le pos du B, alors on ajoute une liaison avec `pos_A=POS_1` et `pos_B=POS_2`
- Après un premier test de la fonction `tok_stanza_for_df`, nous remarquons que le script prend plus de 2 minutes à traiter tous les documents, ainsi nous ajoutons une barre de progression avec le module `tqdm` au lieu de faire des plein de `print()` de progression.
- Réorganisation des colonnes, dans les premiers tests, les nouvelles colonnes (token et pos) se trouve en toute fin, alors que nous les voulons juste après la colonne burst.

## Correction des résultats de postagging (29/05)

### Manuel d'utilisation (`df2csv`, `postagging_for_df`)
- `df2csv` : Fonction de conversion DataFrame → csv/excel
    - `corpus` : `pd.DataFrame` qui peut être crée avec `read_corpus`, `tok_stanza_for_df` et `chunking`.
    - `path` : Fichier de sortie
    - `column` : Affiche que les colonnes sélectionnées. Par défaut, toutes les colonnes
    - `format` : Format de sortie, CSV ou Excel. Par défaut CSV.
- `postagging_for_df` : postagging des bursts avec stanza
    - `dataframe` : `pd.DataFrame` venant de `read_corpus`
    - `new_column` : le nom des deux nouvelles colonnes. Par défaut : token et pos

### Corrections
- Correction de *a* tagger en LAS, alors que c’est un VERB
    - comme *a* est en lui-même un burst, stanza ne le reconnaît pas → ajout d’un test pour corriger ce problème
- Correction de l’emplacement des variables `tok` et `postagging` pour pouvoir accumuler toutes les phrases d’un burst
    ![Version avant correction](img/tagging_av_corr.png)
    * Ce qui est encadré en bleu sont les erreurs à corriger
    ![Version après correction](img/tagging_ap_corr.png)
- Le tag des ponctuations n’a pas été corrigé, l’imbracation des tests n’est pas bien fait
- INTJ : l.34 “équent” n’est pas une interjection
- du ≠ de + le → corriger les du ☑️

### Test à effectuer
- [ ]  `df2csv()`
    - [ ]  avec une sortie en excel
    - [ ]  avec `column` sélectionné
- [ ]  Vérifier dans la sortie si pour *du* le pos a bien changé et que le token n’a pas été divisé en deux ou que le deuxième token ne soit présent

### A faire
- [x]  Finaliser le script de postagging avec `stanza` en ajoutant les modifications mentionnées lors de la réunion 2. **(29/05)**
- [ ]  Préparer les règles pour débuter le chunk avec nltk
- [x]  Pour le test du POS=X, ajouter la transformation du pos suivant aussi → ex: VERB_2 **(28/05)**
- [ ]  Vérifier la sortie de la fonction `df2csv`
    - [x]  df **(29/05)**
    - [ ]  dict → réécrire une fonction pour la conversion : prendre en compte, les token → list[token], pos = list[tuple(token, pos)] , chunk → list[ tuple(chunk, etiquette, syntaxique)]
- [ ]  Write2Json : passer par la fonction df2dict pour avoir la sortie json comme voulu et non pas identique au csv → trop redondant, avec des doublons inutils
- [ ]  Faire une fonction de filtre ⇒ choisir les pos ou token (chunk ?)

## Preprocess before chunking (01/06)
- NLTK chunk : manuel de fonctionnement de la création chunk manuelle.
    - Il demande en entrée une liste de tuple `[(mot, pos)...]`
- Fonction `df2dict` pour avoir la sortie en dictionnaire

## Etiquette syntaxique -- Chunk (02/06)
- `chunking` : prend une liste de `(mot, pos)` et rend en une liste de chunk `(sent, chunk_type)`.
    - Pour facilité la tâche, nous ne prenons que les tag chunk au premier niveau
- correction pour la sortie de `df2dict` : regroupe toutes les métadonnées non utilisé dans “information”

### Problème à corriger
- [x]  à → LAS
- [x]  d’ → ADP

## Chunker complet (03/06)
### Problème rencontré

- Dans la construction du dictionnaire (`df2dict`), la fonction ignore les lignes marquant la pause (*&*) car la fonction regroupe par “ID” et “n_burst”, or lors de l’ajout des pauses, ces deux colonnes n’ont pas de valeurs.
    - Pour corriger ce problème, nous avons ajouté l’ID du burst précédent et sur la base du n_burst précédent, nous ajoutons 0.5. Afin de différencier les pauses des bursts existent et pour qu’ils ne soient pas regroupé en une seule et même ligne (avec tous les n_burst = 0)
- ⚠️ Corriger l.94 (ajouter un test pour les tokens et pos vide)

### Progression

- rename `chunking`-> `chunk_type`
- `chunk_bilou` :
- `chunker` : réunit les deux fonctions précédentes pour l’étiquetage du chunk et donne le choix d’une sortie en dico ou en dataframe
- `dict2json` : fait

Le programme prend en moyenne 5 minutes
```python
# Test depuis `chunker_fr`
from tok_pos import *
from read_write import * 

chemin = "data/corpus"
reader = read_corpus(filesFromFolder(chemin))
test = postagging_for_df(reader)
dico = df2dict(test, True)
chunks = chunker(dico)
for i in range(len(chunks)) :
    if i < 35 :
        print(chunks[f"id_{i}"])
```

## Correction et debug (04/06)
- l.94 : ajouter un test pour `pos="<PAUSE>"` sinon NLTK bloque
- Pour pouvoir utiliser `explode` de pandas, il faut que la taille des valeurs dans les cellules soient identiques
    - id_2803 : le burst est un chiffre `burst=98` → Ajouter un test et une étiquette pour les NUM. Garder la même étiquette pour pos et type_chunk
    - Prendre en compte pos=AUX (ajouter dans `grammar`
    - id_25042 : Un seul DET → ajout d’un type_chunk=DET dans `grammar`
    - id_25060 : chunk vide pour les `token=[nan]` (ce sont les vides de pandas) ⇒ mettre en type_chunk un vide de pandas aussi
- Ajout d’un création des dossiers pour la fonction `df2csv`.

### Test
```python
 # Test 
from read_write import *
from tok_pos import *

# chemin = "data/corpus"
# reader = read_corpus(filesFromFolder(chemin))
# test = postagging_for_df(reader)
# df2csv(test, "data/postag/complet.csv")
chemin = "data/postag/complet.csv"
reader = read_corpus(filesFromFolder(chemin))
dico = df2dict(reader, True)
# chunk_dico = chunker(dico)
# print(chunk_dico["id_25060"])
chunks = chunker(dico, True)
# df2csv(chunks, "data/chunks/complet.csv")
df2csv(chunks, "data/chunks/complet_excel.xlsx", format="excel")
# print(chunks)
```

## Préparation réunion 3 (05/06)
### Préparation des fichiers
```python
# run in this file chunker_fr.py
from read_write import *
from tok_pos import *

chemin = "data/corpus"
reader = read_corpus(filesFromFolder(chemin))
test = postagging_for_df(reader)
df2csv(test, "data/postag/complet_df2csv.csv")
df2csv(test, "data/postag/complet_df2excel.xlsx", format="excel")

dico = df2dict(test, True)
dict2json(dico, "data/postag/complet_df2json.json")

chunk_dico = chunker(dico)
dict2json(chunk_dico, "data/chunks/complet_dict2json.json")

chunks = chunker(dico, True)
df2csv(chunks, "data/chunks/complet_df2csv.csv")
df2csv(chunks, "data/chunks/complet_df2excel.xlsx", format="excel")

df_to_dico = df2dict(chunks, True, True)
dict2json(df_to_dico, "data/chunks/complet_df2json.json")
```
* JSON ne peut pas sérialiser les `pd.NA` il faut convertir en `None`.
 
### Test à effectuer
- [ ]  `df2csv()`
    - [x]  avec une sortie en excel 04/06
    - [ ]  avec `column` sélectionné
- [x]  Vérifier dans la sortie si pour *du* le pos a bien changé et que le token n’a pas été divisé en deux ou que le deuxième token ne soit présent

### A faire pour
- [x]  Finaliser le script de postagging avec `stanza` en ajoutant les modifications mentionnées lors de la réunion 2.
- [x]  Préparer les règles pour débuter le chunk avec nltk 01/06
- [x]  Pour le test du POS=X, ajouter la transformation du pos suivant aussi → ex: VERB_2
- [x]  Vérifier la sortie de la fonction
    - [x]  df
    - [x]  dict → réécrire une fonction pour la conversion : prendre en compte, les token → list[token], pos = list[tuple(token, pos)] , chunk → list[ tuple(chunk, etiquette, syntaxique)] 01/06
- [x]  Write2Json : passer par la fonction df2dict pour avoir la sortie json comme voulu et non pas identique au csv → trop redondant, avec des doublons inutils
- [ ]  Faire une fonction de filtre ⇒ choisir les pos ou token (chunk ?)

### Explication dans le rapport 
#### Progression 21/05 - 05/06

Fonctions conçuent pour aboutir au résultat attendu :

- **read_write.py** :
    - `METADATA` : (constant) définit l’ordre et les colonnes que doient contenir le tableur final
    - `extension` : (fonction) retourne l’extension d’un fichier → *str*
    - `filesFromFolder` : extrait les fichiers d’un dossier donnée → *dict[str, list[str]]*
    - `read_corpus` : Extrait les données selon les colonnes sélectionné d’un fichier csv ou excel → *pd.DataFrame*
    - `df2dict` : Convertie un DataFrame en dict → *dict*
    - `dict2json` : Convertie un dict en fichier json → *<path>.json*
    ⇒ La conversion d’un DataFrame en json est aussi faisable, cepandant la conversion d’un df après traitement (postagging et chunking) rendra le fichier redondant avec les répétitions suite à explode des colonnes voulues. Ainsi il est préférable faire une première conversion (df → dict) pour enlever les doublons
    - `df2csv` : Convertie un DataFrame en fichier CSV ou XSLX → *<path>.<csv|xlsx>*
- **tok_pos.py** :
    - `postagging_for_df` : Tokeniser et postagger → *pd.DataFrame*
- **chunker_fr.py** :
    - `chunk_type` : Etiquetage syntaxique des chunks via NLTK → *list[tuple]*
    - `chunk_bilou` : Etiquetage bilou des groupes chunks syntaxiques après `chunk_type` → *list[tuple]*
    ⇒ L’étiquetage bilou se base sur l’étiquetage syntaxique, et ne tag pas par chunk (token) mais par groupe syntaxique de chunk pour faciliter la tâche
    - `chunker` : Applique les fonctions précédentes sur un dict → *dict | pd.DataFrame*

#### Résultat

##### After postag

**Excel : data/chunks/complet_df2excel.xlsx**

![postag : excel](img/postag_excel.png)

**JSON : data/postag/complet_df2json.json**

![postag : json](img/postag_json.png)

##### After chunk

**Excel : Align_BC/data/chunks/complet_df2excel**

![chunk : excel](img/chunk_excel.png)

**JSON :** 

**data/chunks/complet_df2json.json**   |  **data/chunks/complet_dict2json.json**

![chunk : json](img/chunk_json.png)

#### Questions

- INTJ : l.34 “équent” n’est pas interjection
    
    !Autres exemples INTJ
    
    Autres exemples INTJ
    
    **Comment corriger ?**
    
- Il y a une partie des LAS qui ont été reconnut comme X par le postag de stanza, est-ce qu’il faut corriger ?
- Est-ce qu’il y a besoin d’unifier les **null**, **NaN**, **nan**, **None** pour les vides ?
- Lors de l’étiquetage chunk, les tag <PRON> et <DET> été trouvé seul sans contexte dans les burst. Ainsi il était difficile de savoir sous quelle étiquette syntaxique chunk il fallait les ranger. Pour ne pas bloquer le script, j’ai ranger <PRON> sous **NP** et j’ai créé une étiquette chunk **DET** pour les <DET>. Un conseille ou une correction à apporter ?
- J’ai mis un tag <PAUSE> en pos et chunk pour les marques de pause. Il est possible de les supprimer et changer par du vide.

#### Remarque

##### Durée du programme

Le programme prend environ 7 minutes au total pour le postagging et chunking et avoir une sortie en excel/csv ou json

Le programme de postagging prend le plus de temps, il faut patienter un peu plus de 5 minutes. Ce temps d’attente est surtout dû au grand nombre de ligne que le programme doit parcourir et tagger. Dans ces 5 minutes, l’insertion des pauses (&, <PAUSE>) prend environ 30 secondes. L’explode des lignes avec pandas prend environ 1 minute.

!image.png

Le script pour le chunk et la sauvegarde au format JSON, Excel et CSV prend environ 1 minute. Comme avant de chunker, nous convertissons le DataFrame en dict, le script est plus rapide pour traiter ces données.

##### L’utilisation du chunker

Pour lancer le script pour chunker, il est impérativement obligatoire de lancer le programme de postagging avant. Le chunker de NLTK demande en entrée une liste de tuple avec le token et le postag → `[(token, POS)]`.

## Argparse (08/06)
- `json_reader` : lire un fichier json → *pd.DataFrame | dict*
    - A tester
- argparse
    - [x]  read_write.py
    - [x]  tok_pos.py
    - [ ]  chunker_fr.py
    - [ ]  main_script.py

## Réunion 3 (09/06)
- Corriger les types de chunks et certains POS
    - AUX = 1 chunk VP | Participe Passé = 1 chunk VP
    - PRON = NP
    - PRON + VERB = VP_cl
- Vérifier et corriger :
    - [x]  PP avec adp figé (”loin”…)
    - [x]  du / des / au / aux ⇒ ADP
    - [x]  (INTJ = LAS) + SPACE + SUPPR
    - [x]  adverbes figés 10/06
    - [x]  “de” en fin de burst relié au burst suivant
        - [x]  DET_NP (?)

## Correction postag (10/06)
Progression

- Ajout d’adverbes figés dans la liste
- Correction : les adverbes figés ne sont pas matcher
- Idée de traitement pour le chunk → relier fin et début de burst
    - Créer un dico_token qui range par id un dict comportant [”burst”, “token”, “chunk”]
    - Dans une boucle qui itère `dico_token`, → `if dico["burst"] == dico_token["burst"]` alors on range les chunk dans une liste (`chunk_list`) puis vérifier s’il n’y a pas de doublon
        - Dans la boucle, si le burst est une ligne vide, alors ajouter un chunk (SUPPR/SPACE)
        ![idée de traitement des chunks : screen du terminal](img/terminal.png)
Ligne à vérifier après fin des task

- 715 : emp & êcher
- 732 : trente = NUM → vérification pour chunk
- 4608 : de plus même
- 63946 : sé & curité → burst = NP
- 39008 : décalage de colonne + séparation token faux → *;␣d* `tok={" d", " d"}`

Correction à apporter 

- [x]  dans la grammaire de `chunk_type` ajouter une gestion pour *trente ans* = **NUM+NOUN**

Correction faite :

→ adverbes figés
![Les adverbes figés traités](img/adv_fige.png)
→ gestion des lignes vides = SPACE/SUPPR
![Gestion des lignes vides : SUPPR/SPACE](img/suppr_space.png)

## Correction détaillée chunk 1 (11/06)

### Problème — question

Comment tagger les nombres :

- [ ]  l.6779-6781 : “15 à 25 ans” (*NUM+ADP+NUM+NOUN*)
- [ ]  l.8882 : “de 2 courant” (*ADP+**LAS**+NOUN*) → (*ADP+NUM+NOUN*)
    - [ ]  l.11054 : “de 23000 étudiants” (*ADP+NUM+NOUN*)
- [ ]  l.11654 : “12” = NUM (à garder ?)
La ligne est juste composé du chiffre 12
- [ ]  l.19246 : “la carte du bus est à 200” = NUM (à garder ?)
- [ ]  l.19843 : “juillet 2018…” (*NOUN+NUM*)
- [ ]  l.43085 : “du 09/12/16” (*ADP+**NOUN***)
- [ ]  l.50529-50511 : “8 décembre 2016” (*NUM+NOUN+NUM*)
- [ ]  l.50525-50527 : “Aujourd & ‘hui” (*ADV+<PAUSE>+NOUN*)

### Correction

- 1 nombre (ex: 2, 8…) ont été étiqueté LAS → ajout d’une restriction dans le test d’étiquetage de LAS
l.45 : `pos != "PUNCT"` → `pos not in ["PUNCT", "NUM"]` 
Evite de tagger les ponctuation et les numéro en LAS quand le nombre de caractère est en dessous de 3

### Explication — progression

Pour prendre en compte les burst d’avant et d’après dans l’analyse du chunk, j’ai décidé de ranger tous les listes de (token, pos) dans une seule liste et traiter le tout dans la fonction de `chunk_type`. Ainsi l’analyse chunk prendra en considération tout le contexte.

### Problème — script

- Refaire `chunk_bilou`
    ![Problème des bilou pour les adverbes figés](img/bilou_advFige.png)
- Enlever les doublons → changer `result["chunk"] = []` par une liste simple et transformer la liste en tuple pour enlever les doublons puis affecter à `result["chunk"]`.
❌ 12/06 : possible de supprimer les qui ne sont pas des répétitions successives
- Corriger les `pd.NA` pour qu’il n’y ait plus de faute pour l’extraction dans la conversion avec `to_df=True`.
    ![Dans la conversiont en DataFrame, les `pd.NA` ne sont pas accepté](img/pd_NA.png)
* Vérifier la fin pour voir si cette ligne pose problème ou non 
    ![Ligne 143-145 de chunker_fr.py](img/l_143.png)

## Correction détaillée : chunk 2 (12/06)

### Problème — correction

- [x]  Doublons des chunks en raison d’une itération sur les tokens
    ![Chunk doublé](img/doublons.png)
- [x] Les derniers chunks sont souvent tagger comme null alors que le tag chunk existe
    ![Chunk null](img/null.png)
- [x] Il y a des tokens qui n’ont pas été chunker alors qu’ils ont un pos
    ![Tokens sans chunk](img/ss_chunk.png)
⇒ La plupart est du à un décalage car certain pos n’ont pas été reconnu dans la formation du chunk_type

- [x]  Les VP_cl ne sont pas reconnu → NP + VP
⇒ ajouter une description ou un plus pour le PRON format le VP_cl en utilisant `deprel=expl:com` = PRON_comp
PRON + PRON_cl + VERB
- [x]  Corriger `pd.NA` ou `None` pour ne pas bloquer la convertion avec `to_df = True`.
- [x]  Corriger `chunk_bilou` pour que les adv figés soient comptabilisé comme 1.
- [x]  Prendre en compte les ADP figés

### Ajout de code

- Pour former les VP_cl (*tok_pos.py*)
    ![VP_cl ligne 77-78](img/l_77.png)
→ ne prenait que “y” en compte ⇒ correction 

```python
# Ligne 78
if pos == "PRON" and (word.deprel in ["expl:comp", "expl:pv"]) :
	pos = "PRON_cl"
```

### Correction -- accompli
* ADV/ADP figé
    ![ADV et ADP figé en une ligne](img/adp_adv.png)
* PRON_cl

### Questions chunk
- id_25068 : “… de mesurer …” → ADP + VERB
Pour cette exemple, comme dans la grammaire de construction des chunks, l’étiquette ADP n’apparait que pour le groupe PP (ADP + NP), ainsi lorsque nous avons des ADP seul ou qui se trouve avant un verbe à l’infinitif, le script ne peut pas le reconnaître et le skip.
Pour régler ce problème, est-ce que dans la règle de grammaire, il faut ajouter une étiquette ADP seul ou ranger cette forme (ADP+VERB) dans VP ?
!["de mesurer" difficile à étiqueter](img/de_mesurer.png)
⇒ PP
- l. 37571 : “… Il n’y avait…”
    Comme *y* fait parti des pronoms clitiques français, est-ce une forme de groupe verbal clitique ?
    Si oui, dois-je ajouter dans la règle de grammaire des chunks ce groupe : PRON+ADV+PRON_cl+AUX ?
    !["il y avait" : les formes clitiques](img/fmt_cl.png)
    ⇒ Il y avait = VP
    Il NP / n’ ADVP / y avait VP
- Pour mieux les traiter et distinguer les pronoms clitiques des autres pronoms, j’ai procédé à un ajout de détail dans le pos (⇒ PRON_cl). Cependant, dans les règles grammaticaux du chunk que nous avons défini dans la précédente réunion, la composition d’un VP_cl est obligatoirement  **{<PRON>+<VP>}**. Est-ce correct de le changer ainsi : **{<PRON>?<PRON_cl><VP>}** pour pouvoir traiter les cas comme ci-dessous
    ![PRON_cl + VERB](img/pron_cl.png)
    ⇒ VP

## Correction détaillée : chunk 3 (15/06)
### Choix des types de chunk 

1. Ajout d’un `PP_brok`, pour les prépositions cassé en raison de fautes d’orthographe et de mal reconnaissance des POS de stanza
    
    → Voir l’exemple avec **id_19214** où *de la ou* est en réalité *de là où* considérant comme PP de la phrase précédente.
    
2. Dans les groupes nominaux, ajouter le pos NUM pour traiter les dates que l’on peut considérer comme groupes nominaux temporels
3. Ajout d’un NUM seul pour le type NP pour 
*l.19246 : “la carte du bus est à 200”* 
4. Correction dans VP_cl car les pronoms clitiques ont été repéré et postag par *PRON_cl* plus tôt dans le traitement avec stanza
    Ainsi, nous avons toutes les pronoms clitiques reconnuent
5. Ajout de tag pouvant être sélectionné en tant que PP pour régler les problèmes comme : *de mesurer* avec *mesurer* comme VP, prise en compte des VP_cl qui peuvent avoir le même cas (?)
6. Dans le prétraitement avec stanza, ajout d’un détail pour les adverbes figés ⇒ pos = ADV_fixed
    De même pour les ADP → ADP_fixed
7. A corriger, l’étiquetage des NUM semble quelques fois incorrecte
    ![I identifié comme NUM (id 573)](img/I_num.png)
8. Corriger les ADP seuls
    ![ADP seul](img/adp_seul.png)
9. DET seul
    ![DET seul à corriger pour qu'il y ait une étiquette chunk](img/id_88.png)
10. Comment traiter km/h ? sachant que km=NOUN=NP, /=SYM=UNKNOWN, h=LAS=LAS
    ![Comment traiter km/h](img/km_h.png)

### Correction postag
Pour que les signes comme € ou % ne sont pas reconnus pour LAS
    ![Les signes tagger SYM par stanza sont à garder](img/sym.png)

### Résultat final
#### Commande de test
```python
chemin = "data/corpus"
reader = read_corpus(filesFromFolder(chemin))
postag = postagging_for_df(reader)
dico = df2dict(postag, True)

chemin1 = "data/postag/postag_df.csv"
df2csv(postag, chemin1, format="csv")
df2csv(postag, "data/postag/df_excel.xlsx", format="excel")
dict2json(dico, "data/postag/postag_dict.json")

chunk = chunker(dico)
dict2json(chunk, "data/chunks/chunk_dict.json")

chunk_df = chunker(dico, True)
df2csv(chunk_df, "data/chunks/chunk_df.csv", format="csv")
df2csv(chunk_df, "data/chunks/df_excel.xlsx", format="excel")
```

#### Sorties du test
![Sortie complète (chunk, postag) en tableau csv](img/res_csv.png)
![Sortie complète au format JSON](img/res_json.png)