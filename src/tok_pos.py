"""
    Test differents module of tokenisation, POS and chunk
    Librairies : 
        - stanza
        - NLTK (chunk -> rule)
"""
from read_write import *
import stanza, torch
from tqdm import tqdm
# import argparse
# import pandas as pd

def postagging_for_df(dataframe:pd.DataFrame, new_column:list[str] = ["token", "pos"])->pd.DataFrame :
    """
        Tokenisation, POStagging with stanza of burst
    """
    use_gpu = False
    if torch.cuda.is_available() :
        use_gpu = True

    nlp = stanza.Pipeline(lang="fr", processors="tokenize, pos", use_gpu=use_gpu)

    punct_fort = [".", "!", "?"]

    punct_faible = [",", ";", ":"]

    mwt = ["du", "des", "au", "aux"]

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
        unit=" burst") :

        # Etiquette <SPACE> et <SUPPR> -> distinguer les "lignes vides"
        # Traitement des lignes d'espace/vide
        if pd.isna(burst) or str(burst).strip() == "":
            dataframe.loc[i, "token"] = ""
            if "" in dataframe["charBurst"][i] or "" in dataframe["charBurst"][i] :
                dataframe.loc[i, "pos"] = "SPACE"
            elif "" in dataframe["charBurst"][i] :
                dataframe.loc[i, "pos"] = "SUPPR"
            # dataframe.loc[i, "token"] = pd.NA
            dataframe.loc[i, "pos"] = "" # laisser vide ?
            continue

        

        doc = nlp(str(burst))
        tok = [] # -> token
        postagging = [] # -> postagging

        for sentence in doc.sentences :
            word2token = {
                w.id : tok 
                for tok in sentence.tokens
                for w in tok.words
            }

            idx = 0

            while idx < len(sentence.words) :
                word = sentence.words[idx]     
                token = word.text
                pos = word.pos

                surface = word2token[word.id].text

                # Test pour les exceptions des POS
                if isinstance(token, str) and len(token) <= 3 :
                    if token.lower() in las or (len(token) == 1 and token not in ["y", "a", "à"] and pos != "PUNCT") : # and (pos == "X" and token.lower() != "etc")
                        pos = "LAS" 
                    if idx+1 < len(sentence.words) :
                        pos_ap = sentence.words[idx+1].pos
                        if token.lower() in ["es", "a"] and pos_ap in ["VERB", "ADJ", "NOUN", "ADV"] :
                            pos = "VERB"
                        if token.lower() in ["ses", "d'"] and pos_ap == "NOUN" :
                            pos = "DET"

                    if token in punct_faible :
                        pos = "PUNCT_FAIBLE"
                    elif token in punct_fort :
                        pos = "PUNCT_FORT"

                # La plupart des INTJ sont des LAS
                if pos == "INTJ" :
                    pos = "LAS"

                # Pour DET multi-word token français
                if surface in mwt : 
                    token = surface
                    pos = "DET"
                    idx += 1

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
                if postagging and postagging[-1] == f"{pos}_1" :
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
        unit=" it") :
        
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
                "ID" : dataframe["ID"][i],
                "n_burst" : dataframe["n_burst"][i]+0.5,
                "burst" : "&",
                "token" : "&",
                "pos" : "<PAUSE>"
            }]))

    dataframe = pd.concat(rows, ignore_index=True)

    return dataframe

def main() :

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="Pour extraire ou lire depuis un fichier excel, veuillez installer `openpyxl`"
        )
    
    parser.add_argument("inputpath", type=str, help="CSV, Excel or JSON file")
    parser.add_argument("-o", "--outputfile", type=str, help="Filename to save. Choice the format to save with -f")
    parser.add_argument("-f", "--format", choices=["json", "excel", "csv"], help="Format to save")
    parser.add_argument("--column", type=list, help="Limit which columns were used", default=None)
    parser.add_argument("--limit", type=int, help="Limit lines to process", default=None)

    args = parser.parse_args()
    if args.inputpath.suffix[1:] == ".json" :
        df = json_reader(args.inputpath, "df")
    else :
        df = read_corpus(filesFromFolder(Path(args.path)), args.column, args.limit)
    postagged_df = postagging_for_df(df)

    if args.outputfile : 
        if args.format : 
            out_format = args.format
            if out_format != "json" :
                return df2csv(df, args.outputfile,args.column, args.format)
            else :
                chunked = args.is_chunked or input("Is the inputfile chunked ? (Y/N)").lower() == "y"
                return dict2json(df2dict(postagged_df, True, chunked), args.outputfile)
            

if __name__ == "__main__" :
    main()