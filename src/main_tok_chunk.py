"""
   Interface en ligne de commande permettant de piloter l'ensemble des modules
    du projet : lecture de corpus, annotation morphosyntaxique (POS), chunking,
    filtrage et export des données.

    Le script propose trois commandes principales :
    1. process : exécuter la chaîne de traitement (lecture, POS tagging,
        chunking) puis afficher ou exporter les résultats.
    2. filter : extraire uniquement les lignes ou les entrées JSON répondant à
        des critères sur les métadonnées ou les annotations.
    3. chunk : tester indépendamment les fonctions de détection des types de
        chunks et de génération des étiquettes BILOU.

    Usage
    -----
        python main.py <commande> [options]

    Commandes
    ---------
    process
        Lecture d'un corpus CSV, Excel ou JSON, annotation POS, chunking éventuel
        et export des résultats.

        Exemples :
            python main.py process corpus.csv --postagger
            python main.py process corpus.xlsx --postagger --chunker
            python main.py process corpus.json --json-reader dict
            python main.py process corpus.csv --postagger -o resultat.json -f json

    filter
        Filtrer un corpus selon une ou plusieurs colonnes (POS, type de chunk,
        catégorie, corpus, charge, etc.).

        Exemples :
            python main.py filter corpus.json --columns2filter type_chunk --items2filter NP
            python main.py filter corpus.csv --columns2filter pos_correction --items2filter VERB AUX
            python main.py filter corpus.csv --filter-helper

    chunk
        Tester les fonctions de reconnaissance des types de chunks et des
        annotations BILOU sans traiter un corpus complet.

        Exemples :
            python main.py chunk --chunk-type DET ADJ NOUN
            python main.py chunk --bilou DET ADJ NOUN

    Options principales (process)
    -----------------------------
        -p, --postagger                 réaliser la tokenisation et le POS tagging
        -c, --chunker                   réaliser le chunking
        -o, --outputfile FILE           fichier de sortie
        -f, --format {json,csv,excel}   format d'export
        --column COL [COL ...]          limiter les colonnes importées
        --limit N                       limiter le nombre d'éléments traités
        --json-reader {df,dict}         afficher le contenu d'un fichier JSON
        --is-tagged                     indique que le corpus est déjà annoté en POS
        --is-chunked                    indique que le corpus est déjà chunké

    Options principales (filter)
    ----------------------------
        --columns2filter          colonnes utilisées pour le filtrage
        --items2filter            valeurs recherchées
        --filter-helper           affiche les valeurs disponibles pour chaque
                                colonne filtrable

    Entrées acceptées :
        - fichiers CSV (.csv)
        - fichiers Excel (.xlsx)
        - fichiers JSON (.json)
        - dossiers contenant plusieurs fichiers CSV et/ou Excel

    Sorties :
        - affichage des résultats dans le terminal
        - fichier CSV
        - fichier Excel (.xlsx)
        - fichier JSON
        - DataFrame ou dictionnaire filtré selon les critères demandés
"""
import argparse
# from read_write import *
# from tok_pos import *
from chunker_fr import *

def filtrer(df_or_dict:pd.DataFrame|dict, items:list[str], columns:list[str], outformat:Literal["dico","df"]="df") -> dict|pd.DataFrame :
    """
        Pour filtrer les informations
    """
    
    if columns != "token" :
        if "<PAUSE>" not in items :
            items.append("<PAUSE>")
    else :
        if "&" not in items :
            items.append("&")
    
    if isinstance(df_or_dict, pd.DataFrame) :
        mask = df_or_dict[columns].isin(items).any(axis=1)
        df_filter = df_or_dict[mask]
        if outformat == "dico" :
            return df_filter.to_dict(orient="index")
        return df_filter
    
    results = {}
    for id_, dico in df_or_dict.items():
        for col in columns:
            value = dico.get(col)

            if isinstance(value, list):
                flat_values = [item for sub in value for item in (sub if isinstance(sub, list) else [sub])]
            else:
                flat_values = [value]

            if any(v in items for v in flat_values):
                results[id_] = dico
                break

    if outformat == "df" :
        df_result = pd.DataFrame.from_dict(results, orient="index")
        return df_result
    
    return results

filter_cols = ["input_corpus", "charge", "pos_stanza", "pos_correction", "type_chunk", "negation", "bilou", "categ"]

def main() :
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
            Interface en ligne de commande permettant de piloter l'ensemble des modules
            du projet : lecture de corpus, annotation morphosyntaxique (POS), chunking,
            filtrage et export des données.
        """,
        epilog="Pour extraire ou lire depuis un fichier excel, veuillez installer `openpyxl`"
    )
    subparsers = parser.add_subparsers(dest="Command", required=True)

    process_parser = subparsers.add_parser("process")
    process_parser.add_argument("inputpath", type=str, help="CSV, Excel or JSON file")
    # Action
    process_parser.add_argument("-p", "--postagger", action="store_true", help="To tokenize and postag")
    process_parser.add_argument("-c", "--chunker", action="store_true", help="To chunk")
    # Option
    process_parser.add_argument("-o", "--outputfile", type=str, help="Filename to save. Choice the format to save with -f")
    process_parser.add_argument("-f", "--format", choices=["json", "excel", "csv"], help="Format to save")
    process_parser.add_argument("--json-reader", choices=["df", "dict"], help="To read json file")
    process_parser.add_argument("--column", nargs="+", help="Limit which columns were used", default=None)
    process_parser.add_argument("--limit", type=int, help="Limit lines to process. Give a number", default=None)
    # Mettre en input()
    process_parser.add_argument("--is-tagged", action=argparse.BooleanOptionalAction, help="True if is postagged")
    process_parser.add_argument("--is-chunked", action=argparse.BooleanOptionalAction, help="True if is chunked")

    # Filtre
    filter_parser = subparsers.add_parser("filter")
    filter_parser.add_argument("inputpath", help="File to filter {csv, excel, json}")
    filter_parser.add_argument("-o", "--outputfile", type=str, help="Filename to save. Choice the format to save with -f")
    filter_parser.add_argument("-f", "--format", choices=["json", "excel", "csv"], help="Format to save")
    filter_parser.add_argument("-fi", "--items2filter", nargs="+", help="Informations filter.")
    filter_parser.add_argument("-fc", "--columns2filter", nargs="+", choices=filter_cols)
    filter_parser.add_argument("-fh", "--filter-helper", action="store_true", help="View items can be choice for filter")

    # Fonction seul : Chunk
    chunk_parser = subparsers.add_parser("chunk")
    chunk_parser.add_argument("inputpath", help="File to filter {txt}")
    chunk_parser.add_argument("-ck", "--chunk-type", nargs="+", help=chunk_type.__doc__)
    chunk_parser.add_argument("-b", "--bilou", nargs="+", help="tag BILOU. It's helped by chunk-type")

    args = parser.parse_args()
    inputfile = Path(args.inputpath)
    # Process
    if args.Command == "process" :    
        if inputfile.suffix[1:] == ".json" :
            df = json_reader(args.inputpath, "df")
            dico = json_reader(args.inputpath, "dict")
        else :
            df = read_corpus(filesFromFolder(inputfile), args.column, args.limit)
            dico = df2dict(df)

        if args.postagger :
            df = postagging_for_df(df)
            dico = df2dict(df, True, args.is_chunked)

        if args.chunker :
            if not args.postagger :
                dico = df2dict(df, args.is_tagged)
            df, dico = chunker(dico, True)
        
        # Affichage JSON
        if args.json_reader :
            reader = json_reader(args.inputpath, args.json_reader)
            if args.json_reader == "dict" :
                limit = (
                    args.limit 
                    or int(input(f"Limit output (press ENTER for {len(reader)}) items , press 0 for not print) : ")) 
                    or len(reader)
                )
                idx = 0
                while idx < limit :
                    key = f"id_{idx}"
                    reader_by_id = reader[key]
                    width = max(len(k) for k in reader_by_id.keys())
                    print(f"=== {key} ===")

                    for k, v in reader_by_id.items() :
                        print(f"{k:<{width}} : {v}")
                    print("-" * 50)
                    idx += 1
            else :
                print(reader)
            return
        
        # Affichage
        res = input(f"Limit output (press ENTER for {len(dico)}) items, press 0 for not print) : ")
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

    # Chunk
    elif args.Command == "chunk" :
        width = 25
        if args.chunk_type :
            ck = chunk_type(args.chunk_type)
            for c in ck :
                print(f"{c[0]:<{width}} : {c[1]:<{7}}")
        
        if args.bilou :
            bilou = chunk_bilou(chunk_type(args.bilou))
            for b in bilou :
                print(f"{b[0]:<{width}} : {b[1]:<{7}} {b[3]}") 
        return
    
    # Filter
    elif args.Command == "filter" :
        if inputfile.suffix[1:] == "json" :
            df = json_reader(args.inputpath, "df")
            dico = json_reader(args.inputpath, "dict")
        else :
            df = read_corpus(filesFromFolder(inputfile))
            dico = df2dict(df)

        if args.filter_helper :
            for col in filter_cols :
                uniq_values = df[col].dropna().unique().tolist()
                print(f"{"="*5} {col} {"="*5}\n")
                print(f"values : {uniq_values}")
                print()
            print("By default, <PAUSE> are always in the filter")
            return
        
        if args.items2filter :
            items = args.items2filter
        if args.columns2filter :
            columns = args.columns2filter
        else :
            raise ValueError(f"You must specify at least one column using --columns2filter.")
        
        if args.format == "json" :
            dico = filtrer(dico, items, columns, "dico")
        else :
            df = filtrer(df, items, columns, "df")

    if args.outputfile :
        _format = args.format or input("Choice the output format {csv, excel, json} : ")
        _path = args.outputfile
        if _format == "json" :
            dict2json(dico, _path)
        elif _format in ["csv", "excel"] :
            df2csv(df, _path, format=_format)
        else :
            raise ValueError(f"Unsupported format : {_format}")
        print(f"Save in {Path(_path)}")

if __name__ == "__main__" :
    main()