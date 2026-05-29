"""
    Test differents module of tokenisation, lemmatisation, POS and chunk
    Librairies : 
        - stanza
        - NLTK (chunk -> rule)
"""

from read_write import *
import pandas as pd
import stanza, torch
from tqdm import tqdm

def postagging_for_df(dataframe:pd.DataFrame, new_column:list[str] = ["token", "pos"])->pd.DataFrame :
    """
        wordisation, POS with stanza of burst
    """
    use_gpu = False
    if torch.cuda.is_available() :
        use_gpu = True

    nlp = stanza.Pipeline(lang="fr", processors="tokenize, pos", use_gpu=use_gpu)

    punct_fort = [".", "!", "?"]

    punct_faible = [",", ";", ":"]

    # LAS : Lettre ajouté et/ou supprimée
    las = [
        "e", "ees", "é", "ée", "ées", "ans", 
    ]

    dataframe["token"] = None
    dataframe["pos"] = None

    for i, burst in tqdm(
        enumerate(dataframe["burst"]),
        total=len(dataframe),
        desc="POS tagging",
        unit=" ligne") :

        # Traitement des lignes d'espace/vide
        if pd.isna(burst) or str(burst).strip() == "":
            dataframe.loc[i, "token"] = pd.NA
            continue

        doc = nlp(str(burst))
        tok = [] # -> token
        postagging = [] # -> postagging

        for sentence in doc.sentences :
            idx = 0

            while idx < len(sentence.words) :
                word = sentence.words[idx]     
                token = word.text
                pos = word.pos

                # Test pour les exceptions des POS
                if isinstance(token, str) and len(token) <= 3 :
                    if token.lower() in las or (len(token) == 1 and token not in ["y", "a"] and pos != "PUNCT") : # and (pos == "X" and token.lower() != "etc")
                        pos = "LAS" 
                    if idx+1 < len(sentence.words) :
                        pos_ap = sentence.words[idx+1].pos
                        if token.lower() in ["es", "a"] and pos_ap in ["VERB", "ADJ", "NOUN", "ADV"] :
                            pos = "VERB"
                        if token.lower() == "ses" and pos_ap == "NOUN" :
                            pos = "DET"

                elif token in punct_faible :
                    pos = "PUNCT_FAIBLE"
                elif token in punct_fort :
                    pos = "PUNCT_FORT"
                elif token == "du" :
                    pos = "DET"
                
                # correction de certain pos=X 
                if pos == "X" : 
                    if token == "a" :
                        pos = "VERB"
                    if idx+1 < len(sentence.words) :
                        token_ap = sentence.words[idx+1].text
                        pos_complet = nlp("".join(token+token_ap)).sentences[0].words[0].pos
                        pos_ap = sentence.words[idx+1].pos
                        if pos_ap in ["ADV", "VERB", "ADJ"] and pos_complet == pos_ap :
                            pos = f"{pos_ap}_1"
                # pos=X -> pos=POS_1, alors pos suivant -> pos=POS_2 (liaison)
                if idx > 0 and postagging[-1] == f"{pos}_1" :
                    pos = f"{pos}_2"
                
                # Sauvegarde le tous dans les list
                idx += 1
                tok.append(token)
                postagging.append(pos)
            
            data = {
                "token" : tok,
                "pos" : postagging
            }
            # Range le tous dans le DataFrame
            for nom_column in new_column :
                # position = dataframe.columns.get_loc("burst") + num+1
                dataframe.at[i, nom_column] = data[nom_column]

    #  Réorganise les colonnes avec token et pos juste après burst
    cols = dataframe.columns.tolist()
    burst_idx = cols.index("burst")

    for c in new_column :
        if c in cols :
            cols.remove(c)

    for num, c in enumerate(new_column) :
        cols.insert(burst_idx + 1 + num, c)
    dataframe = dataframe[cols]
    # explode des listes
    dataframe = dataframe.explode(new_column).reset_index(drop=True)

    # Nouvelle ligne vide (token = &) pour marquer les pauses entre les bursts 
    rows = []

    for i in tqdm(range(len(dataframe)), 
        desc="Insertion pause",
        unit=" ligne") :
        
        rows.append(dataframe.iloc[[i]])
        
        # fin de burst : ajout pause
        is_last = ( 
            i == len(dataframe) - 1
            or dataframe["burst"].iloc[i] != dataframe["burst"].iloc[i+1]
            or dataframe["charBurst"].iloc[i] != dataframe["charBurst"].iloc[i+1]
        )

        if is_last :
            rows.append(pd.DataFrame([{
                **{c : pd.NA for c in dataframe.columns},
                "burst" : "&",
                "token" : "&",
                "pos" : "<PAUSE>"
            }]))

    dataframe = pd.concat(rows, ignore_index=True)

    return dataframe

chemin = "Align_BC/data/corpus"
reader = read_corpus(filesFromFolder(chemin), column=["ID", "burst", "charBurst"])
test = postagging_for_df(reader)
df2csv(test, "Align_BC/data/results4")