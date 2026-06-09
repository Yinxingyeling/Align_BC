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
            {(<DET|ADV|ADJ)*>*<(NOUN|PRON)>+<ADJ>*}
        VP : # Groupes verbaux
            {<AUX|VERB>}
        VP_cl : 
            {<PRON>+<VP>}      
        PP : # Groupes prépositionnels
            {<ADP><NP>}
        AP : # Groupes adjectivaux
            {<ADV>*<ADJ>+}
        AVP : # Groupes adverbiaux
            {<(ADV|INTJ)>+}
        CONJ : # Conjonctions
            {<(CCONJ|SCONJ)>}
        PUNCT : # Ponctuations
            {<(PUNCT_FORT|PUNCT_FAIBLE|PUNCT)>}
        LAS : # Lettre(s) ajoutées ou supprimées
            {<LAS>}
        NUM :
            {<NUM>}
        # DET :
        #     {<DET>}
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

    if tagged == [] :
        return []

    for i in range(len(tagged)) :
        burst, tag = tagged[i]
        n = len(burst.split())
        bilou = None
        if n == 1 :
            if tag == "PUNCT" :
                bilou = "O"
            else :
                bilou = "U"

        # Ajout d'un test pour les burst d'après "de"
        if n == 2 :
            bilou = "BL"
        if n > 2 :
            bilou = f"B{'I' * (len(burst.split()) - 2)}L"

        results.append((burst, tag, bilou))
    return results

def chunker(dico:dict, to_df:bool=False, for_sorted:bool=True)-> dict | pd.DataFrame :
    """
        Prend en entrée un dict comportant obligatoirement :
            - key = pos
            - value = list[(token, pos)...]
        to_df = True, if you want a pd.DataFrame
        for_sorted = False, if you want the dict disordered
    """
    results = {}

    for i in range(len(dico)) :
        result = {
            col : dico[f"id_{i}"][col]
            for col in dico["id_1"].keys()
        }

        pos = dico[f"id_{i}"]["pos"]

        if dico[f"id_{i}"]["burst"] in ["", " "] :
            chunks = [(pd.NA, pd.NA, "O")]
        elif dico[f"id_{i}"]["burst"] == "&" :
            chunks = [(dico[f"id_{i}"]["burst"], "PAUSE", "O")]

        elif dico[f"id_{i}"]["pos"] == "NUM" :
            chunks = [(dico[f"id_{i}"]["burst"], "NUM", "U")]

        elif not pos or (isinstance(pos, float) and pd.isna(pos)) :
            chunks = [("", pd.NA, "O")]
        else:
            chunks = chunk_bilou(chunk_type(pos))
            if chunks == [] :
                chunks = [(pd.NA, pd.NA, "O")]
            
        result["chunk"] = chunks
        results[f"id_{i}"] = result

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
            for ck, types, bil in chunk:
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