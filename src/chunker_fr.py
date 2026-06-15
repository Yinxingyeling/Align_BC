"""
    Chunker pour le français. 
    Veuillez installer NLTK for chunk
"""
from tok_pos import *
# import pandas as pd
import nltk.chunk as ck

def chunk_type(tagged:list[tuple]) -> list[tuple]:
    """
        Chunker for french : étiquetage syntaxique des chunks
        * input : [('sur', 'ADP'), ('les', 'DET'), ('paquet', 'NOUN')]
        * output : [('sur les paquet', 'PP')]
    """
    grammar = r"""
        NP : # Groupes nominaux 
            {<(DET|ADV|ADV_fixed|ADJ|NUM)*>*<(NOUN|PRON|PRON_cl|PROPN)>+<ADJ|NUM>*} # + <NUM><NOUN> -> trente/25 ans
            {<NUM>+<SYM>*<NUM>*} # 90%
        VP : # Groupes verbaux
            {<AUX|VERB>}
        VP_cl : # Groupes verbaux clitiques
            {<PRON>?<PRON_cl><VP>} # sinon le VP_cl sont reconnu comme NP+VP 
        PP : # Groupes prépositionnels
            {<(ADP|ADP_fixed)><(NP|VP|VP_cl)>} # "de mesurer"
        AP : # Groupes adjectivaux
            {<(ADV|ADV_fixed)>*<ADJ>+}
        ADVP : # Groupes adverbiaux
            {<(ADV|ADV_fixed|INTJ)>+}
        CONJ : # Conjonctions
            {<(CCONJ|SCONJ)>}
        PUNCT : # Ponctuations
            {<(PUNCT_FORT|PUNCT_FAIBLE|PUNCT)>}
        LAS : # Lettre(s) ajoutée(s) ou supprimée(s)
            {<LAS>}
        PP_brok : 
            {<(ADP|ADP_fixed)>?<DET>?} # "de la" = "de là"-> id_19214 + "pour a son sujet"/"contre Jai" (ADP)
        UNKNOWN :
            {<X|SYM>}
    """
    if not tagged:
        return []

    if all(
        (pd.isna(word) or word == "") and (pd.isna(tag) or tag == "") 
        for word, tag in tagged) :
        return []
    
    chunker = ck.RegexpParser(grammar)
    tree = chunker.parse(tagged)
    
    results = []

    for subtree in tree:
        if hasattr(subtree, 'label'):
            token = [w for w,_ in subtree.leaves()]
            results.append((" ".join(token), subtree.label()))

    return results

def _count_slots(burst: str, tag: str) -> int:
    """
    Calcule le nombre de slots BILOU d'un burst.

    - Si le POS du burst contient FIXED_MARKER, tout le burst est 1 slot
      (cas où chunk_type a regroupé une expression figée seule).
    - Sinon, on cherche dans le burst les sous-chaînes qui correspondent
      à des expressions figées connues (stockées dans FIXED_EXPRESSIONS)
      et on les compte chacune comme 1 slot.
    """
    # Cas : le burst entier est une expression figée (tag marqué)
    if FIXED_MARKER in tag:
        return 1

    words = burst.split()
    n = len(words)
    i = 0
    slots = 0

    while i < n:
        # Cherche la plus longue expression figée commençant à i
        matched_len = _match_fixed_at(words, i)
        if matched_len:
            slots += 1        # toute l'expression figée = 1 slot
            i += matched_len
        else:
            slots += 1        # mot ordinaire = 1 slot
            i += 1

    return slots

def _match_fixed_at(words: list[str], i: int) -> int:
    """
    Retourne la longueur de l'expression figée qui commence à l'index i,
    ou 0 si aucune ne correspond.
    Utilise FIXED_EXPRESSIONS chargé depuis adv_fige.txt et adp_fige.txt.
    """
    for expr in FIXED_EXPRESSIONS:  # déjà trié du plus long au plus court
        end = i + len(expr)
        if end <= len(words):
            if [w.lower() for w in words[i:end]] == expr:
                return len(expr)
    return 0

def _count_slots(burst: str, tag: str) -> int:
    if FIXED_MARKER in tag:
        return 1

    words = burst.split()
    i = 0
    slots = 0

    while i < len(words):
        matched_len = _match_fixed_at(words, i)
        if matched_len:
            slots += 1
            i += matched_len
        else:
            slots += 1
            i += 1

    return slots

def chunk_bilou(tagged:list[tuple]) -> list[tuple] :
    """
        After used `chunk_type`, we can find BILOU
        * B : Begin
        * I : Inside
        * L : Last
        * O : Outside
        * U : Unit
    """
    results = []

    if not tagged:
        return []

    for burst, tag in tagged:
        words = burst.split()
        n = len(words)

        if n == 1:
            bilou = "O" if tag == "PUNCT" else "U"
        else:
            slots = _count_slots(burst, tag)
            if slots == 1:
                bilou = "U"
            elif slots == 2:
                bilou = "BL"
            else:
                bilou = "B" + "I" * (slots - 2) + "L"

        results.append((burst, tag, bilou))

    return results

def delete_first(liste:list) -> list:
    """
        Supprime la première occurrence de la liste
    """
    if list == [] :
        return []
    
    return liste[1:]

def chunker(dico:dict, to_df:bool=False, for_sorted:bool=True)-> dict | pd.DataFrame :
    """
        Prend en entrée un dict comportant obligatoirement :
            - key = pos
            - value = list[(token, pos)...]
        to_df = True, if you want a pd.DataFrame
        for_sorted = False, if you want the dict disordered
    """
    results = {}
    chunk_par_id = {}

    for k in dico.keys():
        pos_id = [
            tuple(t)
            for t in dico[k]["pos"]
            if len(t) >= 2
            and t[1] not in ["<PAUSE>", "<SUPPR>", "<SPACE>", "", " "]
            and not (isinstance(t[1], float) and pd.isna(t[1]))
        ]
        chunk_par_id[k] = chunk_bilou(chunk_type(pos_id)) if pos_id else []

    for id in dico.keys():
        chunk_complet = chunk_par_id[id]
        chunk_idx = 0 
        result = {
            col: dico[id][col]
            for col in dico["id_1"].keys()
        }
        result["chunk"] = []
        for i, tok in enumerate(dico[id]["token"]):
            if not tok or tok in ["&", " "] or (isinstance(tok, float) and pd.isna(tok)):
                chunk = (tok, dico[id]["pos"][i][1], "O")

            elif not chunk_complet:
                chunk = (tok, "", "")

            elif tok not in chunk_complet[0][0]:
                chunk_complet = delete_first(chunk_complet)
                chunk_idx = 0
                if chunk_complet and tok in chunk_complet[0][0]:
                    chunk = chunk_complet[0]
                else:
                    chunk = (tok, "", "")

            else:   
                chunk = chunk_complet[0]
                tokens_du_chunk = chunk_complet[0][0].split()
                chunk_idx += 1
                # Dernier token du chunk → on avance
                if chunk_idx >= len(tokens_du_chunk):
                    chunk_complet = delete_first(chunk_complet)
                    chunk_idx = 0

            
            result["chunk"].append(chunk)
        # Reconstruction pour enlever les doublons
        new_chunk = []
        last_txt = None

        for chunk in result["chunk"]:
            texte = chunk[0]

            if texte != last_txt:
                new_chunk.append(chunk)
                last_txt = texte

        result["chunk"] = new_chunk
        results[id] = result
            
    if for_sorted :
        final = {}
        for i in range(len(results)) :
            order = {
                k : results[f"id_{i}"][k]
                for k in METADATA
                if k in results["id_1"].keys()
            }
            final[f"id_{i}"] = order
        results = final

    if to_df:
        new_columns = ["pos", "chunk"]
        final_df = {}

        for i in range(len(results)):
            final_dico = {
                col: dico[f"id_{i}"][col]
                for col in dico["id_1"].keys()
                if col not in new_columns
            }

            chunk = results[f"id_{i}"]["chunk"]
            postag = [tag for _, tag in results[f"id_{i}"]["pos"]]

            type_chunk = []
            bilou = []
            
            # Aligner les valeurs des colonnes à explode
            for _, types, bil in chunk:
                n_tokens = len(bil) 
                type_chunk.extend([types] * n_tokens)
                bilou.extend(list(bil))

            # vérifier l'alignement avec pos
            if len(type_chunk) != len(postag) or len(bilou) != len(postag):
                n = len(postag)
                type_chunk = (type_chunk + ["O"] * n)[:n]
                bilou = (bilou + ["O"] * n)[:n]

            final_dico["pos"] = postag
            final_dico["type_chunk"] = type_chunk
            final_dico["bilou"] = bilou
            final_df[f"id_{i}"] = final_dico

        df = pd.DataFrame.from_dict(final_df, orient="index").reset_index(drop=True).reindex(columns=METADATA)
        df = df.drop(columns=["chunk"]) # colonne inutile pour df
        df = df.explode(["token", "pos", "type_chunk", "bilou"]).reset_index(drop=True)
        return df
    return results

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



def main() :

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="""Pour extraire ou lire depuis un fichier excel, veuillez installer `openpyxl`"""
        )
    
    parser.add_argument("inputpath", type=str, help="CSV, Excel or JSON file")
    parser.add_argument("-o", "--outputfile", type=str, help="Filename to save. Choice the format to save with -f")
    parser.add_argument("-f", "--format", choices=["json", "excel", "csv"], help="Format to save")
    parser.add_argument("--column", type=list, help="Limit which columns were used", default=None)
    parser.add_argument("--limit", type=int, help="Limit lines to process", default=None)
    # -------- Peut être utilisé seul --------
    parser.add_argument("-ck", "--chunk-type", type=list, help=chunk_type.__doc__)
    parser.add_argument("-b", "--bilou", type=list, help="tag BILOU. It's helped by chunk-type")

    args = parser.parse_args()

    if args.inputpath.suffix[1:] == ".json" :
        dico = json_reader(args.inputpath, "dict")
    else :
        df = read_corpus(filesFromFolder(Path(args.path)), args.column, args.limit)
        dico = df2dict(df)
    
    if args.chunk_type :
        ck = chunk_type(args.chunk_type)
        print(ck)
    
    if args.bilou :
        bilou = chunk_bilou(chunk_type(args.bilou))
        print(bilou)
    
    if args.outputfile : 
        if args.format : 
            out_format = args.format
            if out_format != "json" :
                chunked = chunker(dico)
                return df2csv(chunked, args.outputfile,args.column, args.format)
            else :
                tagged = args.is_tagged or input("Is the inputfile postagged ? (Y/N)").lower() == "y"
                chunked = chunker(dico, True)
                return dict2json(df2dict(chunked, tagged, True), args.outputfile)

    # Affichage
    

if __name__ == "__main__" :
    main()