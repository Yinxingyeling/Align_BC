"""
    Extraction des données depuis les fichiers csv
"""

from pathlib import Path
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
    

def csv2txt(ext_files:dict[str,list[Path]], outputfolder:str="data/txt") :
    """
        Extract data from excel file into txt file
    """
    output_dir = Path(outputfolder)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_files = []

    for files in ext_files.values() :

        for file in files :
            ext = file.suffix.lower()
            if ext == ".xlsx" :
                corpus = pd.read_excel(file, header=1)
            elif ext == ".csv" :
                corpus = pd.read_csv(file)
            else : 
                print(f"Unsupported format : {ext}")
                continue
            
            outputfile = output_dir / f"{file.stem}.txt"

            with open(outputfile, "w", encoding="utf-8") as txt :
                for _, content in corpus.iterrows() :
                    burst = content.get("burst", "")
                    txt.write(f"{burst} & ")

            output_files.append(outputfile)
            print(f"Saved : {outputfile}")
    print(f"All txt files are saved in {output_dir}/")


chemin = "Align_BC/data/corpus"
csv2txt(filesFromFolder(chemin), "Align_BC/data/txt")