"""
    Chunking syntaxique d'un corpus français annoté morphosyntaxiquement à l'aide
    de NLTK (RegexpParser) et attribution des étiquettes BILOU pour chaque token.

    Le script permet de :
    1. Regrouper les tokens annotés en chunks syntaxiques (NP, VP, PP, AP,
        ADVP, CONJ, PUNCT, NUM, UNKNOWN) à partir d'une grammaire de règles.
    2. Appliquer des prétraitements linguistiques afin d'améliorer le chunking,
        notamment pour les adverbes de négation, les adverbes de degré et les
        adjectifs coordonnés postnominaux.
    3. Générer automatiquement les étiquettes BILOU (Begin, Inside, Last,
        Outside, Unit) décrivant la position de chaque token dans son chunk.
    4. Détecter les groupes verbaux exprimant une négation à l'aide des
        annotations morphologiques de Stanza.
    5. Produire un dictionnaire structuré ou un DataFrame alignant, pour chaque
        token, les informations de POS, chunk, type de chunk, négation et BILOU.

    Usage
    -----
        python chunker_fr.py <commande> [options]

    Commandes
    ---------
    process
        Réalise le chunking d'un corpus déjà annoté en POS et exporte les
        résultats.

        Exemples :
            python chunker_fr.py process corpus.json
            python chunker_fr.py process corpus.csv -o corpus_chunk.csv -f csv
            python chunker_fr.py process corpus.json -o corpus_chunk.json -f json

    chunk
        Tester indépendamment les fonctions de reconnaissance des chunks et des
        annotations BILOU.

        Exemples :
            python chunker_fr.py chunk --chunkType "(Le,DET)" "(chat,NOUN)"
            python chunker_fr.py chunk --bilou "(Le,DET)" "(chat,NOUN)"
            python chunker_fr.py chunk --textpath tokens_pos.txt

    Options principales (process)
    -----------------------------
        -o, --outputfile FILE     fichier de sortie
        -f, --format {json,csv,excel}
                                format d'export
        --column COL [COL ...]    limiter les colonnes importées
        --limit N                 limiter le nombre de lignes traitées
        --is-tagged               indique que le corpus possède déjà les
                                annotations POS
        --is-chunked              indique que le corpus est déjà chunké

    Options principales (chunk)
    ---------------------------
        -t, --textpath FILE       fichier texte contenant les couples
                                (token, POS)
        -ck, --chunkType          tester uniquement le chunking
        -b, --bilou              tester le chunking puis les annotations BILOU

    Entrées acceptées :
        - fichiers CSV (.csv)
        - fichiers Excel (.xlsx)
        - fichiers JSON (.json)
        - dictionnaire issu du module de POS tagging
        - liste de couples (token, POS) pour les tests unitaires

    Chunks reconnus :
        - NP      Groupe nominal
        - VP      Groupe verbal
        - PP      Groupe prépositionnel
        - AP      Groupe adjectival
        - ADVP    Groupe adverbial
        - CONJ    Conjonction
        - PUNCT   Ponctuation
        - NUM     Expression numérique
        - UNKNOWN Élément non reconnu ou incomplet

    Sorties :
        - dictionnaire enrichi des annotations de chunk
        - DataFrame aligné au niveau du token
        - fichier CSV
        - fichier Excel (.xlsx)
        - fichier JSON contenant les annotations POS, chunks, négation et BILOU
"""
from tok_pos import *
# import pandas as pd
import nltk.chunk as ck

NEG_ADVERBS = {
    "pas", "plus", "jamais", "rien", "guère", "point",
    "aucunement", "nullement", "personne", "goutte", "mie"
}

def _mark_neg_adv(tagged: list[tuple]) -> list[tuple]:
    """
    Re-tague les adverbes de négation (ADV -> ADV_neg) pour que la
    grammaire puisse les distinguer des autres ADV en fin de VP.
    """
    marked = []
    for word, tag in tagged:
        if tag in ("ADV", "ADV_mwe") and word is not None and word.lower() in NEG_ADVERBS:
            marked.append((word, "ADV_neg"))
        else:
            marked.append((word, tag))
    return marked

def _mark_postnominal_coord_adj(tagged: list[tuple]) -> list[tuple]:
    """
    Marque (ADJ -> ADJ_ap) les adjectifs postnominaux faisant partie
    d'une coordination (NOUN ADJ CCONJ ADJ), pour qu'ils ne soient
    PAS absorbés par le NP mais forment des chunks AP distincts
    reliés par un chunk CONJ.
    """
    NOUNISH = {"NOUN", "PRON", "PROPN", "PRON_cl"}
    tags = [t for _, t in tagged]
    n = len(tags)
    marked = list(tagged)

    for i, (word, tag) in enumerate(tagged):
        if tag != "ADJ":
            continue

        is_postnominal = i > 0 and tags[i - 1] in NOUNISH
        starts_coord = i + 2 < n and tags[i + 1] == "CCONJ" and tags[i + 2] == "ADJ"
        continues_coord = i >= 2 and tags[i - 1] == "CCONJ" and tags[i - 2] == "ADJ"

        if is_postnominal and (starts_coord or continues_coord):
            marked[i] = (word, "ADJ_ap")

    return marked

DEGREE_ADVERBS = {
    "plus", "moins", "aussi", "si", "très", "trop", "bien",
    "assez", "peu", "tellement", "davantage"
}

def _mark_degree_adv(tagged: list[tuple]) -> list[tuple]:
    """
    Re-tague (ADV|ADV_mwe -> ADV_deg) un adverbe de degré/comparaison
    quand il précède immédiatement un ADJ, pour qu'il ne soit pas
    happé par le <ADV>* final du VP (ex: "a" + "plus" + "faibles").
    """
    marked = list(tagged)
    n = len(tagged)
    for i, (word, tag) in enumerate(tagged):
        if tag not in ("ADV", "ADV_mwe"):
            continue
        if word is None or word.lower() not in DEGREE_ADVERBS:
            continue
        next_tag = tagged[i + 1][1] if i + 1 < n else None
        if next_tag == "ADJ":
            marked[i] = (word, "ADV_deg")
    return marked

def chunk_type(tagged:list[tuple]) -> list[tuple]:
    """
        Chunker for french : étiquetage syntaxique des chunks
        * input : [('sur', 'ADP'), ('les', 'DET'), ('paquet', 'NOUN')]
        * output : [("sur les paquet", "PP", 3)]   # (texte, label, n_slots)
    """
    grammar = r"""
        VP :
            # Temps composés
            {(<PRON|PRON_cl>?<ADV|ADV_mwe>*<AUX><ADV|ADV_mwe|ADV_neg>*<VERB>)}
            # Temps simples
            {<PRON>?<ADV|ADV_mwe>*<PRON_cl>*<ADV|ADV_mwe>*<AUX|VERB><ADV_neg>*}
            {<PRON|PRON_cl>?<ADV|ADV_mwe>*<VERB><ADV>*}
            {<AUX|VERB>}
        # VP : # Groupes verbaux
        #     {<(PRON|PRON_cl|ADV)*>*<AUX|VERB>} # sinon le VP_cl sont reconnu comme NP+VP + il y a
        NP : # Groupes nominaux 
            {<(DET|ADV|ADV_mwe|ADV_deg|ADJ|NUM)*>*<(NOUN|PRON|PROPN|PRON_cl)>+<ADJ|NUM>*} # + <NUM><NOUN> -> trente/25 ans
            {<NUM><SYM>} # 90%
            {<DET><ADJ>} # ces derniers...
            {<NP><CCONJ><NP>}
        PP : # Groupes prépositionnels
            {<(ADP|ADP_mwe|SYM_adp)>+<(NP|VP|NUM)>?} # "de mesurer"
        AP : # Groupes adjectivaux
            {<(ADV|ADV_mwe|ADV_deg)>*<(ADJ|ADJ_ap)>+}
        ADVP : # Groupes adverbiaux
            {<(ADV|ADV_mwe|INTJ|ADV_neg)>+}
        CONJ : # Conjonctions
            {<(CCONJ|SCONJ|SYM_conj)>}
        PUNCT : # Ponctuations
            {<(PUNCT_FORT|PUNCT_FAIBLE|PUNCT)>}
        NUM :
            {<NUM>}
        UNKNOWN :
            {<X|SYM|LAS>} # Lettre(s) ajoutée(s) ou supprimée(s)
            {<(ADP|ADP_mwe)>?<DET>} #"de la" = "de là"-> id_19214 + "pour a son sujet"/"contre Jai" (ADP)
    """
    if not tagged:
        return []

    if all(
        (pd.isna(word) or word == "") and (pd.isna(tag) or tag == "") 
        for word, tag in tagged) :
        return []
    
    tagged = _mark_degree_adv(tagged)
    tagged = _mark_neg_adv(tagged)
    tagged = _mark_postnominal_coord_adj(tagged)
    
    chunker = ck.RegexpParser(grammar)
    tree = chunker.parse(tagged)

    results = []
    for subtree in tree:
        if hasattr(subtree, 'label'):
            leaves = subtree.leaves()
            token = [w for w, _ in leaves]
            # n_slots = nombre d'ids d'origine ayant composé ce chunk
            results.append((" ".join(token), subtree.label(), len(leaves)))
        else:
            word, _ = subtree
            results.append((word, "UNKNOWN", 1))

    return results

def make_bilou(slots:int, burst:str, unit_brok=False):
    """
        Génère la séquence BILOU correspondant au nombre de slots 
        - Mode standard :
            * 1 slot -> U
            * 2 slots -> BL
            * n slots -> B + I*(n-2) + L

        - Mode Unit_brok (les unités cassées) :
            * 1 slot  -> B
            * 2 slots -> BI
            * n slots -> B + I*(n-1)
    """
    if unit_brok and burst.isalpha():
        return "B" + "I" * max(0, slots - 1)

    if slots == 1:
        return "U"
    if slots == 2:
        return "BL"
    return "B" + "I" * (slots - 2) + "L"

def chunk_bilou(tagged: list[tuple]) -> list[tuple]:
    """
        After used `chunk_type`, we can find BILOU
    """
    results = []
    if not tagged:
        return []

    for burst, tag, n_slots in tagged:
        if n_slots == 1:
            bilou = "O" if tag == "PUNCT" else "U"
        else:
            bilou = make_bilou(n_slots, burst, unit_brok=(tag == "UNKNOWN"))
        results.append((burst, tag, bilou))

    return results

def is_negative(chunk:str, types:str, nlp=None)->int :
    """
        Prend en entrée un chunk VP et vérifie s'il y a la négation à l'intérieur
        Retourne 1 si oui, sinon 0
    """
    neg = 0
    if types == "VP" :
        doc = nlp(chunk)
        for sentence in doc.sentences :
            for word in sentence.words :
                if word.feats and "Polarity=Neg" in word.feats :
                    neg = 1
    return neg


def chunker(dico:dict, to_df:bool=False, for_sorted:bool=True)-> dict | pd.DataFrame :
    """
        Prend en entrée un dict comportant obligatoirement :
            - key = pos
            - value = list[(token, pos)...]
        to_df = True, if you want a pd.DataFrame
                -> return df, dico
        for_sorted = False, if you want the dict disordered
    """
    # liste de tous les tuples (token, pos)
    tok_pos_complet = []
    for k in dico.keys() :
        pos = dico[k].get("pos_correction") or []
        t_k = [
            tuple(t)
            for t in pos
            if len(t) >= 2
            and t[1] not in ["<PAUSE>", "<SUPPR>", "<SPACE>", "", " "] # vérifie les tag pos
            and t != (None, None)
            and not (isinstance(t[1], float) and pd.isna(t[1]))
        ]
        tok_pos_complet.extend(t_k)
    
    ck_complet = chunk_bilou(chunk_type(tok_pos_complet))
    # Ajout d'un offset à 0 pour compter le nombre de fois où le set de chunk a été utilisé
    ck_complet = [(tok, type_ck, bilou, 0) for tok, type_ck, bilou in ck_complet]

    results = {}
    for idx in tqdm(
        dico.keys(), 
        total=len(dico.keys()), 
        desc="Chunking...") :

        result = {
            col : dico[idx][col]
            for col in dico["id_1"].keys()
        }
        token = dico[idx].get("token") or []
        pos_list = dico[idx]["pos_correction"]

        # Extraire le pos (gère les tuples et valeurs None)
        pos = "".join(
            p if p is not None else ""
            for _, p in pos_list
        )

        # Détecter les tokens spéciaux via le pos
        special_tags = {"<PAUSE>", "<SUPPR>", "<SPACE>"}
        pos_values = {p for _, p in pos_list if p is not None}
        is_special = bool(pos_values & special_tags)

        # Remettre les vides (SUPPR, SPACE, PAUSE) — ou token vraiment vide
        if is_special or token is None or token in ["", " ", [""], [" "]]:
            # type_chunk = le tag spécial trouvé, sinon pos brut
            type_chunk = next((p for _, p in pos_list if p in special_tags), pos)
            print(type_chunk)
            result["chunk"] = [("", type_chunk, "O", 0)]
        else :
            ck_total = []
            ck_count = 0
            tok_count = len(token)

            for one_ck in ck_complet:
                tok_of_ck, type_ck, bilou_of_ck, offset = one_ck

                tokens_restants_dans_ck = len(bilou_of_ck) - offset
                tokens_restants_dans_burst = tok_count - ck_count

                apport = min(tokens_restants_dans_ck, tokens_restants_dans_burst)
                ck_count += apport
                neg = is_negative(tok_of_ck, type_ck, nlp)
                # Slice du bilou selon offset et apport 
                bilou_slice = bilou_of_ck[offset: offset + apport]
                ck_total.append((tok_of_ck, type_ck, bilou_slice, neg))

                if ck_count >= tok_count:
                    new_offset = offset + apport
                    if new_offset >= len(bilou_of_ck):
                        ck_complet = ck_complet[1:]  # chunk entièrement consommé
                    else:
                        ck_complet[0] = (tok_of_ck, type_ck, bilou_of_ck, new_offset)  # déborde → update offset
                    break
                else:
                    ck_complet = ck_complet[1:]  # chunk fini pour ce burst
                
            result["chunk"] = ck_total
        results[idx] = result

    if for_sorted :
        final = {}
        for i in results.keys() :
            order = {
                k : results[i][k]
                for k in METADATA
                if k in results["id_1"].keys()
            }
            final[i] = order
        results = final

    if to_df:
        new_columns = ["pos_stanza", "pos_correction", "chunk", "negation"]
        final_df = {}

        for i in results.keys():
            final_dico = {
                col: dico[i][col]
                for col in dico["id_1"].keys()
                if col not in new_columns
            }

            chunk = results[i]["chunk"]
            postag_stanza = [tag for _, tag in results[i]["pos_stanza"]]
            postag = [tag for _, tag in results[i]["pos_correction"]]
            cks = []
            type_chunk = []
            bilou = []
            negation = []
            
            # Aligner les valeurs des colonnes à explode
            for ck, types, bil, neg in chunk:
                n_tokens = len(bil) 
                cks.extend([ck]*n_tokens)
                type_chunk.extend([types] * n_tokens)
                bilou.extend(list(bil))
                negation.extend([neg] * n_tokens)

            # vérifier l'alignement avec pos
            if len(type_chunk) != len(postag) or len(bilou) != len(postag) or len(cks) != len(postag) or len(negation) != len(postag):
                n = len(postag)
                cks = (cks + [None] * n)[:n]
                type_chunk = (type_chunk + ["O"] * n)[:n]
                bilou = (bilou + ["O"] * n)[:n]
                negation = (negation + [0]*n)[:n]

            final_dico["chunk"] = cks
            final_dico["pos_stanza"] = postag_stanza
            final_dico["pos_correction"] = postag
            final_dico["type_chunk"] = type_chunk
            final_dico["bilou"] = bilou
            final_dico["negation"] = negation
            final_df[i] = final_dico

        df = pd.DataFrame.from_dict(final_df, orient="index").reset_index(drop=True).reindex(columns=METADATA)
        # df = df.drop(columns=["chunk"]) # colonne inutile pour df
        df = df.explode(["token","pos_stanza", "pos_correction", "chunk", "type_chunk", "negation", "bilou"]).reset_index(drop=True)
        return df, results
    return results

def main() :

    parser = argparse.ArgumentParser(
        description="""
            Chunking syntaxique d'un corpus français annoté morphosyntaxiquement à l'aide
            de NLTK (RegexpParser) et attribution des étiquettes BILOU pour chaque token.
        """,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="""Pour extraire ou lire depuis un fichier excel, veuillez installer `openpyxl`"""
        )
    subparsers = parser.add_subparsers(dest="Command", required=True)

    process_parser = subparsers.add_parser("process")
    process_parser.add_argument("inputpath", help="CSV, Excel or JSON file")
    process_parser.add_argument("-o", "--outputfile", help="Filename to save. Choice the format to save with -f")
    process_parser.add_argument("-f", "--format", choices=["json", "excel", "csv"], help="Format to save")
    process_parser.add_argument("--column", nargs="+", help="Limit which columns were used", default=None)
    process_parser.add_argument("--limit", type=int, help="Limit lines to process", default=None)
    # input()
    process_parser.add_argument("--is-tagged", action=argparse.BooleanOptionalAction, help="True if is postagged")
    process_parser.add_argument("--is-chunked", action=argparse.BooleanOptionalAction, help="True if is chunked")
    # -------- Peut être utilisé seul --------
    chunk_parser = subparsers.add_parser("chunk")
    chunk_parser.add_argument("-t", "--textpath", help="Text file while tuple of token and pos by line (ex: (token, pos))")
    chunk_parser.add_argument("-ck", "--chunkType", nargs="+", help=chunk_type.__doc__)
    chunk_parser.add_argument("-b", "--bilou", nargs="+", help="tag BILOU. It's helped by chunk-type")

    args = parser.parse_args()

    if args.Command == "process" :
        inputpath = Path(args.inputpath)
        if inputpath.suffix[1:] == "json" :
            dico = json_reader(inputpath, "dict")
        else :
            df = read_corpus(filesFromFolder(inputpath), args.column, args.limit)
            dico = df2dict(df)
        
        chunked = chunker(dico)

        if args.outputfile : 
            if args.format : 
                out_format = args.format
                if out_format != "json" :
                    return df2csv(chunked, args.outputfile,args.column, args.format)
                else :
                    tagged = (
                        args.is_tagged 
                        if args.is_tagged is not None
                        else input("Is the input file postagged ? (Y/N)").lower() == "y"
                    )
                    chunked = chunker(dico, True)
                    return dict2json(df2dict(chunked, tagged, True), args.outputfile)

        # Affichage
        res = input(f"Limit output (press ENTER for {len(dico)}) items : ")
        limit_arg = getattr(args, "limit", None)
        limit = (
            limit_arg
            if limit_arg is not None   
            else (len(dico) if res == "" else int(res))
        )
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

    elif args.Command == "chunk" :
        if args.textpath :
            path = Path(args.textpath)
            list_pos = open(path, "r", encoding="utf-8").readlines()
        else :
            list_pos = args.chunkType or args.bilou
            # list_pos = [i if isinstance(i, tuple) else tuple(i) for i in (args.chunkType or args.bilou)]
            print(list_pos)
        res_ck = chunk_type(list_pos)
        if args.bilou :
            bilou = chunk_bilou(res_ck)
            print(f"{"\n".join(b for b in bilou)}")
            return
        print(f"{"\n".join(b for b in res_ck)}")

        
if __name__ == "__main__" :
    main()