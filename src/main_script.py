"""
   Actionneur des scripts 
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
        df_filter = df_or_dict[df_or_dict[columns].isin(items)]
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

def main() :
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
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
    filter_parser.add_argument("-fi", "--informations2filter", nargs="+", help="Informations filter.")
    filter_parser.add_argument("-fc", "--colums2filter", nargs="+", choices=["token", "pos", "chunk-type", "bilou"])
    filter_parser.add_argument("-fh", "--filter-helper", action="store_true", help="View items can be choice for filter")

    # Fonction seul : Chunk
    chunk_parser = subparsers.add_parser("chunk")
    chunk_parser.add_argument("-ck", "--chunk-type", nargs="+", help=chunk_type.__doc__)
    chunk_parser.add_argument("-b", "--bilou", nargs="+", help="tag BILOU. It's helped by chunk-type")

    args = parser.parse_args()

    # Process
    if args.Command == "process" :

        if args.inputpath.suffix[1:] == ".json" :
            df = json_reader(args.inputpath, "df")
            dico = json_reader(args.inputpath, "dict")
        else :
            df = read_corpus(filesFromFolder(Path(args.path)), args.column, args.limit)
            dico = df2dict(df)

        if args.postagger :
            df = postagging_for_df(df)
            dico = df2dict(df, True, args.is_chunked)

        if args.chunker :
            dico = chunker(dico)
        
        # Affichage JSON
        if args.json_reader :
            reader = json_reader(args.inputpath, args.json_reader)
            if args.json_reader == "dict" :
                limit = (
                    args.limit 
                    or int(input(f"Limit output (press ENTER for {len(reader)}) items : ")) 
                    or len(reader)
                )
                idx = 0
                while idx < limit :
                    key = f"id_{idx}"
                    reader_by_id = reader[key]
                    width = max(len(k) for k in reader_by_id)
                    print(f"=== {key} ===")

                    for k, v in reader_by_id.values() :
                        print(f"{k:<{width}} : {v}")
                    print("-" * 50)
                    idx += 1
            else :
                print(reader)
            return
        
        # Affichage
        if args :
            limit = (
                args.limit 
                or int(input(f"Limit output (press ENTER for {len(dico)}) items : ")) 
                or len(dico)
            )
            idx = 0
            while idx < limit :
                key = f"id_{idx}"
                dico_by_id = dico[key]
                width = max(len(k) for k in dico_by_id)
                print(f"=== {key} ===")

                for k, v in dico_by_id.values() :
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
    
    # Filter
    elif args.Command == "filter" :
        NotImplemented


if __name__ == "__main__" :
    main()