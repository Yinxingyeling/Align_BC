"""
    Test differents module of tokenisation, POS and chunk
    Librairies : 
        - stanza
        - NLTK (chunk -> rule)
"""
from read_write import *
import stanza, torch, re
from tqdm import tqdm
# import argparse
# import pandas as pd

def process_words(sentence, tok, postagging, matches_dict=None, nlp=None):
    """
        Traite les mots d'une phrase stanza et les ajoute aux listes tok et postagging
    """
    punct_fort = [".", "!", "?"]

    punct_faible = [",", ";", ":"]
    
    mwt = ["du", "des", "au", "aux"]

    las = [
        "e", "ees", "é", "ée", "ées", 
    ]

    word2token = {
        w.id : t
        for t in sentence.tokens
        for w in t.words
    }

    idx = 0
    while idx < len(sentence.words) :
        word = sentence.words[idx]
        token = word.text
        pos = word.pos
        surface = word2token[word.id].text

        # Adverbes figés : reformer les marques par les adv
        if matches_dict:
            matched_key = next((k for k in matches_dict if token == k), None)
            if matched_key:
                token = matches_dict[matched_key]
                pos = "ADV"

        # Test pour les exceptions des POS
        if isinstance(token, str) and len(token) <= 3 :
            if token.lower() in las or (len(token) == 1 and token not in ["y", "a", "à"] and pos not in ["PUNCT", "NUM", "SYM"]) :
                pos = "LAS"
            if idx+1 < len(sentence.words) :
                pos_ap = sentence.words[idx+1].pos
                if token.lower() in ["es", "a"] and pos_ap in ["VERB", "ADJ", "NOUN", "ADV"] :
                    pos = "VERB"
                if token.lower() in ["ses", "d'"] and pos_ap == "NOUN" :
                    pos = "DET"
            
            # Corriger "I" que stanza reconnait pour NUM
            if pos == "NUM" and token == "I" :
                pos = "LAS"

            if token in punct_faible :
                pos = "PUNCT_FAIBLE"
            elif token in punct_fort :
                pos = "PUNCT_FORT"

        # La plupart des INTJ sont des LAS
        if pos == "INTJ" :
            pos = "LAS"

        # Pour DET multi-word token français
        if surface.lower() in mwt:
            token = surface
            upos_tok = word2token[word.id]
            if (len(upos_tok.words) == 2 and upos_tok.words[0].upos == "ADP" and upos_tok.words[1].upos == "DET") :
                pos = "ADP"
                idx += 1
            else:
                pos = "DET"

        # Ajout d'un détail pour avoir les VP_cl
        if pos == "PRON" and (word.deprel in ["expl:comp", "expl:pv"]) :
            pos = "PRON_cl"

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

        idx += 1
        tok.append(token)
        postagging.append(pos)

    return tok, postagging

FIXED_MARKER = "_fixed"
adv_path = Path(__file__).parent / "ressources" / "adv_fige.txt"
adp_path = Path(__file__).parent / "ressources" / "adp_fige.txt"

adv_fige = Path(adv_path).read_text(encoding="utf-8").splitlines()
adp_fige = Path(adp_path).read_text(encoding="utf-8").splitlines()

def _build_fixed_expressions(adv: list[str], adp: list[str]) -> list[list[str]]:
    return sorted(
        [expr.strip().lower().split() for expr in adv + adp if expr.strip()],
        key=len, reverse=True
    )

FIXED_EXPRESSIONS = _build_fixed_expressions(adv_fige, adp_fige)

def match_fixed_expr(matches:list, pos:str, burst, nlp):
    tok = []
    postagging = []
    pos = pos.upper()
    match_dict = {f"__{pos}{j}__": r for j, r in enumerate(matches, start=1)}
    pattern = "|".join(re.escape(r) for r in sorted(matches, key=len, reverse=True))

    # Split du burst en gardant les adv/adp figés comme séparateurs
    parts = re.split(f"({pattern})", burst, flags=re.IGNORECASE)

    for part in parts :
        if not part or not part.strip() :
            continue

        # adverbe figé → 1 token, POS=ADV
        if re.fullmatch(pattern, part.strip(), flags=re.IGNORECASE) :
            tok.append(part.strip())
            postagging.append(f"{pos}{FIXED_MARKER}")

        # stanza
        else :
            doc_part = nlp(part.strip())
            for sentence in doc_part.sentences :
                tok, postagging = process_words(sentence, tok, postagging, matches_dict=match_dict, nlp=nlp)
    return tok, postagging

def postagging_for_df(dataframe:pd.DataFrame, new_column:list[str] = ["token", "pos"])->pd.DataFrame :
    """
        Tokenisation, POStagging with stanza of burst
    """
    use_gpu = False
    if torch.cuda.is_available() :
        use_gpu = True

    nlp = stanza.Pipeline(lang="fr", processors="tokenize, pos, lemma, depparse", use_gpu=use_gpu)

    dataframe["token"] = None
    dataframe["pos"] = None

    for i, burst in tqdm(
        enumerate(dataframe["burst"]),
        total=len(dataframe),
        desc="POS tagging",
        unit=" burst") :

        # Traitement des lignes d'espace/vide
        if pd.isna(burst) or str(burst).strip() == "" :
            burst = dataframe["charBurst"][i]
            burst_str = "" if pd.isna(burst) else str(burst)
            dataframe.loc[i, "token"] = ""
            dataframe.loc[i, "pos"] = ""
            if "⌫" in burst_str or "⌦" in burst_str :
                dataframe.loc[i, "pos"] = "<SUPPR>"
            elif "␣" in burst_str :
                dataframe.loc[i, "pos"] = "<SPACE>"
            continue

        tok = []
        postagging = []

        # Gestion des adverbes figés
        for pos, exprs in (("ADV", adv_fige), ("ADP", adp_fige)):
            matches = [r for r in exprs if r and r.lower() in str(burst).lower()]
            if matches:
                tok, postagging = match_fixed_expr(matches, pos, burst, nlp)
                break
        else :
            adv_dict = {}
            doc = nlp(str(burst))
            for sentence in doc.sentences :
                tok, postagging = process_words(sentence, tok, postagging, matches_dict=adv_dict, nlp=nlp)

        data = {
            "token" : tok,
            "pos"   : postagging
        }

        for nom_column in new_column :
            dataframe.at[i, nom_column] = data[nom_column]

    # Réorganise les colonnes avec token et pos juste après burst
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

        is_last = (
            i == len(dataframe) - 1
            or dataframe["burst"].iloc[i] != dataframe["burst"].iloc[i+1]
            or dataframe["charBurst"].iloc[i] != dataframe["charBurst"].iloc[i+1]
        )

        if is_last :
            rows.append(pd.DataFrame([{
                **{c : pd.NA for c in dataframe.columns},
                "ID"      : dataframe["ID"][i],
                "n_burst" : dataframe["n_burst"][i]+0.5,
                "burst"   : "&",
                "token"   : "&",
                "pos"     : "<PAUSE>"
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