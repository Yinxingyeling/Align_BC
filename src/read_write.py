"""
    Extraction pu écriture des données depuis les fichiers csv ou excel

"""
from pathlib import Path
from typing import Literal
from collections import defaultdict
import pandas as pd

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

    all_column = [
        "ID",	"charge",	"outil",	"n_burst",	
        "debut_burst",	"duree_burst",	"duree_pause",	"duree_cycle",	
        "pct_burst",	"pct_pause",	"longueur_burst",	
        "burst",    "token",   "pos",  "type_chunk",   "schema_annot", # BILOU
        "startPos",	"endPos",	"docLength",	
        "categ",	"charBurst",	"ratio"
    ]

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
                    col for col in all_column
                    if col in available_columns
                ]
            else:
                select_column = [
                    col for col in all_column
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

def df2dict(dataframe:pd.DataFrame, column:str|list[str], limit:None|int=None) -> dict :
    """
        Transforme un DataFrame en dict
    """
    pass

def dict2json(dataframe:dict, path:Path|str) :
    """
        S'utilise avec df2dict() pour ne pas avoir les doublons
        Rend un fichier json
    """
    import json
    pass

def df2csv(dataframe:pd.DataFrame, path:Path|str, column:str|list[str]|None=None, format:Literal["csv", "excel"]="csv") :
    """
        Transforme un DataFrame en fichier csv ou excel
    """
    if isinstance(column, str) :
        column = [
            col for col in column.split()
            if col in dataframe.columns.tolist()
        ]

    if format == "excel" :
        path = path + ".xlsx"
        dataframe.to_excel(
            excel_writer=path,
            columns=column,
        )

        return f"Conversion fini. Fichier csv sauvegarder : {path}"

    path = path + ".csv"
    
    dataframe.to_csv(
        path_or_buf=path,
        columns=column,
        encoding="utf-8",
        index=False
    )

    return f"Conversion fini. Fichier csv sauvegarder : {path}"