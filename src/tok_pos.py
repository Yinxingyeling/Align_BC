"""
    Tokenisation et annotation morphosyntaxique (POS tagging) d'un corpus de
    production écrite à l'aide de Stanza, avec corrections linguistiques adaptées
    au corpus étudié.

    Le script permet de :
    1. Tokeniser chaque burst (segment de frappe) avec Stanza.
    2. Attribuer les étiquettes morphosyntaxiques (POS) d'origine produites par
        Stanza.
    3. Appliquer une série de corrections manuelles et automatiques pour traiter
        les erreurs de POS, les expressions figées (ADV/ADP), les multi-word
        tokens, les ponctuations, les clitiques, les fautes de frappe et certains
        cas particuliers du corpus.
    4. Produire un DataFrame où chaque token occupe une ligne, avec les colonnes
        de tokenisation, POS d'origine et POS corrigées.
    5. Ajouter un token spécial "&" entre deux bursts afin de matérialiser les
        pauses d'écriture pour les traitements ultérieurs (chunking, analyses).

    Usage
    -----
        python postagging.py inputpath [options]

    Exemples :
        python postagging.py corpus.csv
        python postagging.py corpus.xlsx -o corpus_pos.csv -f csv
        python postagging.py corpus.json -o corpus_pos.json -f json
        python postagging.py corpus/ --limit 1000

    Options utiles :
        -o, --outputfile FILE      fichier de sortie
        -f, --format {json,csv,excel}
                                format d'export
        --column COL [COL ...]     limiter les colonnes importées
        --limit N                  limiter le nombre de lignes traitées
        --is-chunked               indique que le corpus possède déjà les
                                annotations de chunks (utile lors d'un export
                                JSON)

    Entrées acceptées :
        - un fichier CSV (.csv)
        - un fichier Excel (.xlsx)
        - un fichier JSON
        - un dossier contenant plusieurs fichiers CSV et/ou Excel

    Colonnes ajoutées :
        token            tokenisation du burst
        pos_stanza       étiquette POS produite par Stanza
        pos_correction   étiquette POS après corrections spécifiques au corpus

    Sorties :
        - DataFrame tokenisé et annoté
        - fichier CSV
        - fichier Excel (.xlsx)
        - fichier JSON structuré par burst, avec les annotations POS
"""
from read_write import *
import re
from tqdm import tqdm
# import argparse
# import pandas as pd

def get_nlp():
    import stanza, torch
    use_gpu = False
    if torch.cuda.is_available() :
        use_gpu = True

    return stanza.Pipeline(lang="fr", processors="tokenize, pos, lemma, depparse", use_gpu=use_gpu)

def process_words(sentence, tok:list, origine_pos:list, postagging:list, burst_idx:tuple, matches_dict:dict=None, nlp=None) -> tuple[list]:
    """
        Traite les mots d'une phrase stanza et les ajoute aux listes tok et postagging
    """
    punct_fort = [".", "!", "?"]

    punct_faible = [",", ";", ":"]
    
    mwt = ["du", "des", "au", "aux"]

    las = [
        "e", "ees", "é", "ée", "ées", "u", "es"
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
        stanza_pos = word.pos
        pos = word.pos
        surface = word2token[word.id].text

        if token == "" :
            idx += 1
            tok.append(token)
            origine_pos.append(stanza_pos)
            postagging.append("<ARTIFACT>")
            continue

        # Adverbes figés : reformer les marques par les adv
        if matches_dict:
            matched_key = next((k for k in matches_dict if token == k), None)
            if matched_key:
                token = matches_dict[matched_key]
                pos = "ADV"

        # Test pour les exceptions des POS
        if isinstance(token, str) and len(token) <= 3 :
            if token.lower() in las or (len(token) == 1 and token not in ["y", "a", "à", "h"] and pos not in ["PUNCT", "NUM", "SYM"]) :
                pos = "LAS"
            if idx+1 < len(sentence.words) :
                pos_ap = sentence.words[idx+1].pos
                if token.lower() == "a" and pos_ap in ["VERB", "ADJ", "NOUN", "ADV"] :
                    pos = "AUX"
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
        if pos == "PRON" and (word.deprel in ["expl:comp", "expl:pv", "iobj", "obj"]) :
            pos = "PRON_cl"
        # Pour les cas: est-ce (-ce = nsubj)
        if pos == "PRON" and (word.deprel in ["nsubj", "expl:subj"]) and "-" in token : 
            pos = "PRON_cl"

        # Distinction PRON et PRON_relatif
        if pos == "PRON" and word.feats and "PronType=Rel" in word.feats :
            pos = "PRON_rel"

        # Catch verbes à l'infinitif pour traiter les cas :
        # de mesurer, de pouvoir travailler...
        if pos == "VERB" and (word.feats == "VerbForm=Inf") :
            pos = "VERB_inf"

        # correction de certain pos=X
        if pos == "X" :
            if token == "a" :
                pos = "AUX"
            if idx+1 < len(sentence.words) :
                token_ap = sentence.words[idx+1].text
                pos_complet = nlp("".join(token+token_ap)).sentences[0].words[0].pos
                pos_ap = sentence.words[idx+1].pos
                if pos_ap in ["ADV", "VERB", "ADJ"] and pos_complet == pos_ap :
                    pos = f"{pos_ap}_1"

        # pos=X -> pos=POS_1, alors pos suivant -> pos=POS_2 (liaison)
        if postagging and postagging[-1] == f"{pos}_1" :
            pos = f"{pos}_2"

        # Détail des SYM (km/h où "/" = ADP et permis/voiture où "/" = CONJ)
        if pos == "SYM":
            if tok and tok[-1] == "km":
                pos = "SYM_adp"
            elif idx + 1 < len(sentence.words):
                next_pos = sentence.words[idx + 1].pos
                next_text = sentence.words[idx + 1].text
                if next_text == "h":
                    pos = "SYM_adp"
                elif idx > 0:
                    prev_pos = sentence.words[idx - 1].pos
                    if prev_pos == "NUM" and next_pos == "NUM":
                        pos = "SYM_adp"   # 3/4
                    elif prev_pos == next_pos:
                        pos = "SYM_conj"  # et/ou, permis/voiture
        
        # Correction des dates (chiffrés) -> NOUN de stanza

        if re.fullmatch(r"\d+/\d+/\d+", token) and pos == "NOUN" :
            pos = "NUM" 
        
        # Faute de frappe reconnu pour PRON_cl (unique)
        if burst_idx == ("F+S17", np.int64(15.0)) and (pos == "PRON_cl" and token == "se") :
            pos = "DET"
        if burst_idx == ("F+S1", np.int64(14.0)) and (pos == "ADJ" and token == "crée") :
            pos = "VERB"

        # Correction pour des bursts précis
        change_ou2adv = {("F+S17", np.int64(45)), ("F+S29", np.int64(76)), ("F-S19", np.int64(11)), ("F-S6", np.int64(42)), ("F-S9", np.int64(23)), ("P+S20", np.int64(39)), ("P-S19", np.int64(48)), ("P-S19", np.int64(57)), ("P-S24", np.int64(12)), ("P-S8", np.int64(63)), ("R+S3", np.int64(73)), ("R+S3", np.int64(75)), ("R+S3", np.int64(125)), ("R+S4", np.int64(54)), ("R-S10", np.int64(104)), ("R-S6", np.int64(1)), ("R-S7", np.int64(96))}
        change_ou2cconj = {("F+S1", np.int64(4)), ("P-S21", np.int64(54)), ("R-S20", np.int64(17))}
        change_es2verb = {("F+S19", np.int64(52)), ("F-S11", np.int64(15)), ("F-S28", np.int64(82))} # 4237 et 10534 sont des corrections
        change_2unknow = {("F-S17", np.int64(38)), ("R+S9", np.int64(60)), ("F+S5", np.int64(28))}

        if burst_idx in change_ou2adv and (pos == "CCONJ" and token == "ou") :
            pos = "ADV"
        if burst_idx in change_ou2cconj and (pos == "ADV" and token == "où") :
            pos = "CCONJ"
        if burst_idx in change_es2verb and (pos == "LAS" and token == "es") :
            pos = "AUX"
        if burst_idx in change_2unknow and ((pos == "CCONJ" and token == "ou") or (pos == "LAS" and token == "es")):
            pos = "X"
        if burst_idx == ("F+S13", np.int64(51)) and (pos == "PRON" and token == "tout") :
            pos = "ADV"

        idx += 1
        tok.append(token)
        origine_pos.append(stanza_pos)
        postagging.append(pos)

    return tok, origine_pos, postagging

FIXED_MARKER = "_mwe" # Multiword expression

adv_path = Path(__file__).parent / "ressources" / "adv_fige.txt"
adp_path = Path(__file__).parent / "ressources" / "adp_fige.txt"
conj_path = Path(__file__).parent / "ressources" / "conj_fige.txt"
noun_path = Path(__file__).parent / "ressources" / "noun_fige.txt"
det_path = Path(__file__).parent / "ressources" / "det_fige.txt"

adv_fige = Path(adv_path).read_text(encoding="utf-8").splitlines()
adp_fige = Path(adp_path).read_text(encoding="utf-8").splitlines()
conj_fige = Path(conj_path).read_text(encoding="utf-8").splitlines()
noun_fige = Path(noun_path).read_text(encoding="utf-8").splitlines()
det_fige = Path(det_path).read_text(encoding="utf-8").splitlines()

def _build_fixed_expressions(adv: list[str], adp: list[str], conj: list[str], noun: list[str], det:list[str]) -> list[list[str]]:
    return sorted(
        [expr.strip().lower().split() for expr in adv + adp + conj + noun + det if expr.strip()],
        key=len, reverse=True
    )

FIXED_EXPRESSIONS = _build_fixed_expressions(adv_fige, adp_fige, conj_fige, noun_fige, det_fige)

def match_fixed_expr(matches:list, pos:str, burst:str, idx_burst:tuple, nlp):
    tok = []
    origine_pos = []
    postagging = []
    pos = pos.upper()
    match_dict = {f"__{pos}{j}__": r for j, r in enumerate(matches, start=1)}
    pattern = "|".join(re.sub(r"\\ ", r"\\s+", re.escape(r.strip())) for r in sorted(matches, key=len, reverse=True))

    # Split du burst en gardant les adv/adp figés comme séparateurs
    parts = re.split(f"({pattern})", burst, flags=re.IGNORECASE)

    for part in parts :
        if not part or not part.strip() :
            continue

        # adverbe figé → 1 token, POS=ADV
        if re.fullmatch(pattern, part.strip(), flags=re.IGNORECASE) :
            tok.append(part.strip())
            origine_pos.append(pos)
            postagging.append(f"{pos}{FIXED_MARKER}")

        # stanza
        else :
            doc_part = nlp(part.strip())
            for sentence in doc_part.sentences :
                tok, origine_pos, postagging = process_words(sentence, tok, origine_pos, postagging, idx_burst, matches_dict=match_dict, nlp=nlp)
    return tok, origine_pos, postagging

def postagging_for_df(dataframe:pd.DataFrame, nlp=get_nlp() ,new_column:list[str] = ["token", "pos_stanza", "pos_correction"])->pd.DataFrame :
    """
        Tokenisation, POStagging with stanza of burst
    """
    dataframe["token"] = None
    dataframe["pos_stanza"] = None
    dataframe["pos_correction"] = None

    for i, burst in tqdm(
        enumerate(dataframe["burst"]),
        total=len(dataframe),
        desc="POS tagging",) :

        # Traitement des lignes d'espace/vide
        if pd.isna(burst) or str(burst).strip() == "" :
            burst = dataframe["charBurst"][i]
            burst_str = "" if pd.isna(burst) else str(burst)
            dataframe.loc[i, "token"] = ""
            dataframe.loc[i, "pos_stanza"] = ""
            dataframe.loc[i, "pos_correction"] = ""
            if "⌫" in burst_str or "⌦" in burst_str :
                dataframe.loc[i, "pos_correction"] = "<SUPPR>"
            elif "␣" in burst_str :
                dataframe.loc[i, "pos_correction"] = "<SPACE>"
            continue
        
        tok = []
        origine_pos = []
        postagging = []

        # Gestion des expressions figées
        for pos, exprs in (("ADV", adv_fige), ("ADP", adp_fige), ("CONJ", conj_fige), ("NOUN", noun_fige), ("DET", det_fige)):
            burst_norm = re.sub(r"\s+", " ", str(burst).lower()).strip()
            matches = sorted(
                [r for r in exprs if re.sub(r"\s+", " ", r.lower()).strip() in burst_norm],
                key=lambda x:len(x.split()),
                reverse=True
                )
            if matches:
                tok, origine_pos, postagging = match_fixed_expr(matches, pos, str(burst), (dataframe["ID"][i], dataframe["n_burst"][i]), nlp)
                break
        else :
            adv_dict = {}
            doc = nlp(str(burst))
            for sentence in doc.sentences :
                tok, origine_pos, postagging = process_words(sentence, tok, origine_pos, postagging, (dataframe["ID"][i], dataframe["n_burst"][i]), matches_dict=adv_dict, nlp=nlp)

        data = {
            "token" : tok,
            "pos_stanza" : origine_pos,
            "pos_correction"   : postagging
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
                **{c : None for c in dataframe.columns},
                "ID"             : dataframe["ID"][i],
                "charge"         : dataframe["charge"][i],
                "n_burst"        : dataframe["n_burst"][i]+0.5,
                "burst"          : "&",
                "token"          : "&",
                "pos_correction" : "<PAUSE>"
            }]))

    dataframe = pd.concat(rows, ignore_index=True)

    return dataframe

def main() :

    parser = argparse.ArgumentParser(
        description="""
            Tokenisation et annotation morphosyntaxique (POS tagging) d'un corpus de
            production écrite à l'aide de Stanza, avec corrections linguistiques adaptées
            au corpus étudié.
        """,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="Pour extraire ou lire depuis un fichier excel, veuillez installer `openpyxl`"
        )
    
    parser.add_argument("inputpath", type=str, help="CSV, Excel or JSON file")
    parser.add_argument("-o", "--outputfile", type=str, help="Filename to save. Choice the format to save with -f")
    parser.add_argument("-f", "--format", choices=["json", "excel", "csv"], help="Format to save")
    parser.add_argument("--column", nargs="+", help="Limit which columns were used", default=None)
    parser.add_argument("--limit", type=int, help="Limit lines to process", default=None)
    # input()
    parser.add_argument("--is-tagged", action=argparse.BooleanOptionalAction, help="True if is postagged")
    parser.add_argument("--is-chunked", action=argparse.BooleanOptionalAction, help="True if is chunked")

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
            

    # Affichage
    res = input(f"Limit output (press ENTER for {len(dico)}) items : ")
    limit_arg = getattr(args, "limit", None)
    limit = (
        limit_arg
        if limit_arg is not None   
        else (len(dico) if res == "" else int(res))
    )
    chunked = (
        args.is_chunked
        if args.is_chunked is not None
        else input("Is the input file chunked? (Y/N) ").strip().lower() == "y"
    )
    dico = df2dict(postagged_df, True, chunked)
    idx = 0
    while idx < limit :
        key = f"id_{idx}"
        dico_by_id = dico[key]
        width = max(len(k) for k in dico_by_id.keys())
        print(f"=== {key} ===")

        for k, v in dico_by_id.items() :
            print(f"{k:<{width}} : {v}")
        print("-" * 50)
        idx += 1

if __name__ == "__main__" :
    main()