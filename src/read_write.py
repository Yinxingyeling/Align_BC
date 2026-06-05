"""
    Extraction des données depuis les fichiers csv ou excel.
    Ecriture d'objet dict ou pd.DataFrame vers des fichiers json ou csv/excel
"""
from pathlib import Path
from typing import Literal
from collections import defaultdict
import pandas as pd
import argparse

METADATA = [
    "ID",   "input_corpus", "charge",	"outil",	"n_burst",	
    "debut_burst",	"duree_burst",	"duree_pause",	"duree_cycle",	
    "pct_burst",	"pct_pause",	"longueur_burst",	
    "burst",    "token",   "pos", "chunk", "type_chunk",   "bilou", # BILOU
    "startPos",	"endPos",	"docLength",	
    "categ",	"charBurst",	"ratio"
]

def extension(filename:str)->str :
    return Path(filename).suffix[1:]

def filesFromFolder(foldername:str)->dict[str,list[str]] :
    """
        Extract files from folder
    """
    folder = Path(foldername)
    if not folder.exists():
        raise FileNotFoundError(f"{foldername} does not exist")
    
    if folder.is_file() :
        return {extension(folder): [folder]}
    
    files = sorted(folder.iterdir())

    if not files :
        raise FileNotFoundError(f"Not files exists in this folder {foldername}")
    
    results = defaultdict(list)
    for file in files :
        if file.is_file() :
            results[extension(file)].append(Path(file))

    return dict(results)
    
def read_corpus(ext_files:dict[str, list[str]], column:str|list[str]="all", limit:None|int=None)-> pd.DataFrame :
    """
        Extrait les données selon les colonnes voulues du fichier csv ou excel
        - column = "all" # prend en compte toutes les colonnes
        - column = ["burst", "categ"] # ne prend que les burst et catégories de pause

        Pandas for excel used openpyxl, make sure you have installed !
    """
    results = []
    
    for files in ext_files.values() :

        for file in files :
            # Vérifie l'extension (csv or excel)
            ext = file.suffix.lower()
            if ext == ".xlsx" :
                corpus = pd.read_excel(file, header=1)
            elif ext == ".csv" :
                corpus = pd.read_csv(file)
            else : 
                print(f"Unsupported format : {ext}")
                continue
            
            # Vérifie les colonnes : si lecture du fichiers avant ou après traitement 
            # new_column = ["token", "lemma", "pos", type_chunk", "schema_annot"]
            available_columns = corpus.columns.tolist()

            if column == "all":
                select_column = [
                    col for col in METADATA
                    if col in available_columns
                ]
            else:
                select_column = [
                    col for col in METADATA
                    if col in column and col in available_columns
                ]

            results.append(corpus[select_column])

    # Fusion dans un nouvel DataFrame
    final_df = pd.concat(results, ignore_index=True)
    # Transforme les NaN (vide) de pandas par " "
    if "burst" in final_df.columns : 
        final_df["burst"] = final_df["burst"].fillna(" ")

    if limit :
        final_df = final_df[:limit]
    
    return final_df


def df2dict(df:pd.DataFrame, is_tagged:bool=False, is_chunked:bool=False, for_sorted:bool=True) -> dict:
    """
        DataFrame to dict
        * is_tagged = True : if the df have runned `postagging_for_df`
        * is_chunked = True : if the df have runned `chunker`
    """
    results = {}
    grouped = df.groupby(["ID","n_burst"])

    corpus_map = {
        "F": "Formulation",
        "P": "Plannification",
        "R": "Révision"
    }

    for idx, (_, group) in enumerate(grouped):
        first = group.iloc[0]

        result = {
            col: first[col]
            for col in METADATA
            if col in df.columns
        }

        if "ID" in result:
            prefix = str(result["ID"])[0]
            result["input_corpus"] = corpus_map.get(prefix)

        if "burst" in df.columns:
            result["burst"] = first["burst"]

        if is_tagged and {"token","pos"}.issubset(df.columns):
            result["token"] = group["token"].tolist()
            result["pos"] = list(zip(group["token"], group["pos"]) )
        # Directement utiliser les fonctions chunk_type et chunk_bilou
        if is_chunked and {"chunk", "type_chunk", "bilou"}.issubset(df.columns):
            chunks = []
            current_tokens = []
            current_bilou = []
            # Corriger la partie token -> chunk 
            for _, row in group.iterrows():
                token = row.get("token", row.get("burst",""))
                bilou = row["schema_annot"]
                chunk_type = row["type_chunk"]

                if bilou in ["B","I"]:
                    current_tokens.append(token)
                    current_bilou.append(bilou)

                elif bilou == "L":
                    current_tokens.append(token)
                    current_bilou.append(bilou)
                    chunks.append((" ".join(current_tokens), "".join(current_bilou), chunk_type))
                    # Initialise à 0
                    current_tokens = []
                    current_bilou = []

                elif bilou in ["U","O"]:
                    chunks.append((token, bilou, chunk_type))

            result["chunk"] = chunks

        results[f"id_{idx}"] = result

    if for_sorted :
        final = {}
        for i in range(len(results)) :
            order = {
                k : results[f"id_{i}"][k]
                for k in METADATA
                if k in results["id_1"].keys()
            }
            final[f"id_{i}"] = order
        return final

    return results

def dict2json(dataframe:dict, path:Path|str) :
    """
        S'utilise avec `df2dict(for_sorted=True)` ou `chunker(for_sorted=True)` pour ne pas avoir les doublons
        Rend un fichier json
    """
    import json
    if isinstance(dataframe, dict) :
        with open(path, "w", encoding="utf-8") as f :
            json.dump(dataframe, f, ensure_ascii=False, indent=4, default=lambda obj: None if obj is pd.NA else str(obj))
    else : 
        print(f"{dataframe} isn't a dict object")
    

def df2csv(dataframe:pd.DataFrame, path:Path|str, column:str|list[str]|None=None, format:Literal["csv", "excel"]="csv") :
    """
        Transforme un DataFrame en fichier csv ou excel
    """
    if isinstance(column, str) :
        column = [
            col for col in column.split()
            if col in dataframe.columns.tolist()
        ]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if format == "excel" :
        dataframe.to_excel(
            excel_writer=path,
            columns=column,
        )

        return f"Conversion fini. Fichier csv sauvegarder : {path}"
    
    dataframe.to_csv(
        path_or_buf=path,
        columns=column,
        encoding="utf-8",
        index=False
    )

    return f"Conversion fini. Fichier csv sauvegarder : {path}"