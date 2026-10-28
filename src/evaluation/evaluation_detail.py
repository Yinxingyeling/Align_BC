import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import sys
    import marimo as mo
    from pathlib import Path
    parent_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(parent_dir))
    return Path, mo


@app.cell
def _():
    from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, accuracy_score, classification_report
    from read_write import filesFromFolder, read_corpus, METADATA
    from typing import Literal
    from collections import defaultdict
    import matplotlib.pyplot as plt
    import seaborn as sns
    import pandas as pd
    import numpy as np

    return (
        accuracy_score,
        classification_report,
        confusion_matrix,
        f1_score,
        filesFromFolder,
        np,
        pd,
        plt,
        precision_score,
        read_corpus,
        recall_score,
        sns,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Création des données

    Nous allons construire 3 DataFrames afin d'évaluer le chunker :
    * `pred_init` sont les prédictions initiaux du chunker.
    * `gold` représente 3980 lignes (tokens) annotées manuellement
    * `pred_gold` est l'alignement de `gold` sur `pred_init`. Ce DataFrame stock les prédictions du chunker correspondant aux données annotées manuellement.
    """)
    return


@app.cell
def _(Path, filesFromFolder, read_corpus):
    # Ouverture du fichier déjà annoté
    corpus_chunked = "../data/chunks/csv_chunk.csv"
    gold_annot = "evaluation/gold_annotation.csv"
    pred_init= read_corpus(filesFromFolder(Path(corpus_chunked)), sep=";")
    gold = read_corpus(filesFromFolder(Path(gold_annot)))
    return gold, pred_init


@app.cell
def gold_output(gold):
    gold
    return


@app.cell
def _(gold, pred_init):
    cols = ["ID","input_corpus", "charge", "outil", "n_burst"]
    pred_gold = pred_init.merge(gold[cols].drop_duplicates(), on=cols, how="inner")
    return cols, pred_gold


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Vérification d'alignement des données

    Vérifier si l'alignement de `pred_gold` a bien été réalisé. Point de contrôle entre `gold` et `pred_gold`:
    * Même tokens
    * Même ordre
    * Même observation
    """)
    return


@app.cell
def _(gold, pred_gold):
    # 1. Vérifier les colonnes nécessaires
    for df in [gold, pred_gold]:
        assert {"ID", "token"}.issubset(df.columns), \
            "Colonnes ID ou token manquantes."

    # 2. Vérifier le nombre de lignes
    assert len(gold) == len(pred_gold), \
        "Les DataFrames n'ont pas le même nombre de lignes."

    # 3. Réinitialiser les index pour comparer ligne par ligne
    g = gold.reset_index(drop=True)
    p = pred_gold.reset_index(drop=True)

    # 4. Vérifier l'alignement des ID
    assert g["ID"].equals(p["ID"]), \
        "Les ID diffèrent ou ne sont pas dans le même ordre."

    # 5. Vérifier l'alignement des tokens
    assert g["token"].equals(p["token"]), \
        "Les tokens diffèrent ou ne sont pas dans le même ordre."

    print("Contrôle réussi : gold et pred_gold sont alignés.")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Calcul des métriques - 1

    Après contrôle des données, nous allons maintenant évaluer les résultats du chunker. Cinq calculs d'évaluation via la librairie scikit-learn :
    * Précision
    * Rappel
    * F-mesure
    * Accurracy
    * Matrice de confusion

    Trois niveaux d'évaluation pour aboutir à notre but final.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Avant de procédé à la première évaluation de nos données, nous allons d'abord diviser le corpus gold afin d'avoir un échantillon à l'écart si après les résultats de la première évaluation nous amène à un changement des règles du chunker.
    """)
    return


@app.cell(hide_code=True)
def _(gold, np):
    # Catégorisation thématique à partir des ID du corpus.
    topic_map = {
        "F+S1": "Tabac",
        "F+S11": "Étudiants et transports",
        "F+S21": "Étudiants et transports",
        "F+S28": "Médecine",
        "F+S5": "Étudiants et transports",
        "P+S12": "Médecine",
        "P+S13": "Médecine",
        "P-S29": "Étudiants et transports",
        "P-S3": "Tabac",
        "R+S2": "Médecine",
        "R+S23": "Tabac",
        "R+S24": "Étudiants et transports",
        "R+S3": "Médecine",
        "R+S8": "Étudiants et transports",
        "R-S13": "Étudiants et transports",
        "R-S4": "Étudiants et transports",
        "R-S8": "Médecine",
        "R-S9": "Médecine",
    }
    copy_gold = gold.copy()
    copy_gold["genre"] = copy_gold["ID"].map(topic_map)
    if copy_gold["genre"].isna().any():
        raise ValueError("Certains ID n'ont pas de genre attribué.")

    # Une unité indivisible = un burst, identifié par ID + n_burst.
    # Stratification par type d'activité et genre, sans jamais couper un burst.
    rng = np.random.default_rng(42)
    groups = (
        copy_gold.groupby(["ID", "n_burst", "input_corpus", "genre"], dropna=False)
            .size().rename("n_rows").reset_index()
    )
    groups["split"] = ""

    for _, indices in groups.groupby(["input_corpus", "genre"], sort=False).groups.items():
        indices = list(indices)
        rng.shuffle(indices)
        target = 0.70 * groups.loc[indices, "n_rows"].sum()
        assigned_70 = 0
        for i in indices:
            n = int(groups.loc[i, "n_rows"])
            if abs(assigned_70 + n - target) <= abs(assigned_70 - target):
                groups.loc[i, "split"] = "gold_70"
                assigned_70 += n
            else:
                groups.loc[i, "split"] = "gold_30"

    assignment = groups.set_index(["ID", "n_burst"])["split"]
    copy_gold["_split"] = [
        assignment.loc[(row.ID, row.n_burst)] for row in copy_gold.itertuples()
    ]

    gold_70 = copy_gold.loc[copy_gold["_split"] == "gold_70"].drop(columns=["genre", "_split"]).copy().reset_index(drop=True)
    gold_30 = copy_gold.loc[copy_gold["_split"] == "gold_30"].drop(columns=["genre", "_split"]).copy().reset_index(drop=True)
    # copy_gold = copy_gold.drop(columns=["genre", "_split"]).copy()

    # Vérification : aucun burst n'est présent dans les deux sous-corpus.
    b70 = set(zip(gold_70["ID"], gold_70["n_burst"]))
    b30 = set(zip(gold_30["ID"], gold_30["n_burst"]))
    assert b70.isdisjoint(b30), "Un burst a été coupé entre les deux sous-corpus."

    print(f"gold: {len(copy_gold)} lignes")
    print(f"gold_70: {len(gold_70)} lignes ({len(gold_70)/len(copy_gold):.1%})")
    print(f"gold_30: {len(gold_30)} lignes ({len(gold_30)/len(copy_gold):.1%})")
    return (gold_70,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Token-token

    Une première évaluation token-token pour mesurer la qualité de la prédiction des frontières et des positions des chunks. Pour cette partie, nous utiliserons la précision, le rappel, la f-mesure et l'accurracy en comparant les étiquettes BILOU de chaque token entre `gold` et `pred_gold`.
    * Précision : parmi les étiquettes prédites comme appartenant à une classe, quelle proportion est correcte ?
    * Rappel : parmi les étiquettes de référence de cette classe, quelle proportion a été retrouvée ?
    * F1-score : compromis entre précision et rappel.
    * Accuracy : proportion totale de tokens dont l’étiquette est correcte.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Préparons les données d'évaluation
    * gold_dev : les annotations manuelles de référence.
    * pred_gold_dev : les prédictions originales du chunker pour ces mêmes tokens
    """)
    return


@app.cell
def _(cols, gold_70, pred_init):
    # Préparation des données
    gold_dev = gold_70
    pred_gold_dev = pred_init.merge(gold_dev[cols].drop_duplicates(), on=cols, how="inner")
    return gold_dev, pred_gold_dev


@app.cell
def _(
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    pd,
    precision_score,
    recall_score,
):
    def evaluation(y_gold, y_pred) :
        # Accurracy
        accuracy = accuracy_score(y_gold, y_pred)
        print(f"Accurracy : {accuracy}\n")

        # Précision
        precision = precision_score(y_gold, y_pred, average="macro" ,zero_division=0)
        print(f"Précision : {precision}\n")

        # Rappel
        rappel = recall_score(y_gold, y_pred, average="macro" ,zero_division=0)
        print(f"Rappel : {rappel}\n")

        # F-mesure
        f1 = f1_score(y_gold, y_pred, average="macro" ,zero_division=0)
        print(f"F-mesure : {f1}\n")

        # Détails des résultats
        report = classification_report(y_gold, y_pred, zero_division=0)
        print(f"Détail par étiquette : \n{report}\n")

        # Matrice de confusion
        labels = sorted(set(y_gold) | set(y_pred))
        cm = confusion_matrix(y_gold, y_pred, labels=labels)

        df_cm = pd.DataFrame(
            cm,
            index=[f"Gold_{label}" for label in labels],
            columns=[f"Pred_{label}" for label in labels]
        )
        return accuracy, precision, rappel, f1, report, cm, labels, df_cm

    return (evaluation,)


@app.cell
def _(plt, sns):
    def fig_confusion_matrix(cm, labels, title=str, color="Blues") :
        fig, ax = plt.subplots(figsize=(8, 6))

        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            cmap=color,
            xticklabels=labels,
            yticklabels=labels,
            ax=ax,
        )

        ax.set_xlabel("Étiquette prédite")
        ax.set_ylabel("Étiquette réelle (Gold)")
        ax.set_title(title)

        fig.tight_layout()

        return fig

    return (fig_confusion_matrix,)


@app.cell
def _(evaluation, gold_dev, pred_gold_dev):
    y_gold_bilou = gold_dev["bilou"]
    y_pred_bilou = pred_gold_dev["bilou"]

    accuracy_bilou, precision_bilou, rappel_bilou, f1_bilou, report_bilou, cm_bilou, labels_bilou, df_cm_bilou = evaluation(y_gold_bilou, y_pred_bilou)
    return (
        accuracy_bilou,
        cm_bilou,
        df_cm_bilou,
        f1_bilou,
        labels_bilou,
        precision_bilou,
        rappel_bilou,
        report_bilou,
    )


@app.cell(hide_code=True)
def _(
    accuracy_bilou,
    df_cm_bilou,
    f1_bilou,
    mo,
    precision_bilou,
    rappel_bilou,
    report_bilou,
):
    mo.md(f"""
    ### Métriques globales

    | Métrique | Score |
    |:---|---:|
    | Accuracy | {accuracy_bilou:.4f} |
    | Précision macro | {precision_bilou:.4f} |
    | Rappel macro | {rappel_bilou:.4f} |
    | F-mesure macro | {f1_bilou:.4f} |

    ### Rapport de classification

    {report_bilou}

    ### Matrice de confusion

    {df_cm_bilou.to_html()}
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Types de chunks

    Un deuxième niveau pour évaluer les types de chunks afin de vérifier si le chunker attribut bien la bonne catégorie aux segments détectés.

    Pour cela, nous allons comparer la catégorie `type_chunk` entre `gold` et `pred_gold` en calculant la précision, le rappel et le score f1 pour chaque type, ainsi qu'une moyenne globale.
    """)
    return


@app.cell
def _(evaluation, gold_dev, pred_gold_dev):
    y_true_type = gold_dev["type_chunk"]
    y_pred_type = pred_gold_dev["type_chunk"]

    accuracy_type, precision_type, rappel_type, f1_type, report_type, cm_type, labels_type, df_cm_type = evaluation(y_true_type, y_pred_type)
    return (
        accuracy_type,
        cm_type,
        df_cm_type,
        f1_type,
        labels_type,
        precision_type,
        rappel_type,
        report_type,
    )


@app.cell(hide_code=True)
def _(
    accuracy_type,
    df_cm_type,
    f1_type,
    mo,
    precision_type,
    rappel_type,
    report_type,
):
    mo.md(f"""
    ### Métriques globales

    | Métrique | Score |
    |:---|---:|
    | Accuracy | {accuracy_type:.4f} |
    | Précision macro | {precision_type:.4f} |
    | Rappel macro | {rappel_type:.4f} |
    | F-mesure macro | {f1_type:.4f} |

    ### Rapport de classification

    {report_type}

    ### Matrice de confusion

    {df_cm_type.to_html()}
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Les chunks complets

    Enfin, nous évaluons dans ce dernier niveau si le chunker détecte les bons segments avec les bonnes frontières et les bonnes catégories. Le critère principal : un chunk de `pred_gold` est correct uniquement si ses frontières de début et de fin et son type correspond exactement à celui du `gold`.

    Pour cela, nous calculerons la précision, le rappel et la f-mesure.
    """)
    return


@app.function
def extraire_chunks_depuis_colonnes(df):
    chunks = set()

    df = df.reset_index(drop=True).copy()

    # Position de chaque token dans son ID
    df["_position"] = df.groupby("ID", sort=False).cumcount()

    # Les chunks sont identifiés par leur texte et leur type
    masque = (
        df["chunk"].notna()
        & df["type_chunk"].notna()
        & ~df["type_chunk"].eq("<PAUSE>")
        & ~df["type_chunk"].eq("<SUPPR>")
    )

    # Chaque séquence contiguë partageant ID, chunk et type
    # devient un chunk distinct.
    for identifiant, groupe in df.groupby("ID", sort=False):
        indices = groupe.index
        actif = False
        debut = None
        chunk_courant = None
        type_courant = None
        precedent = None

        for idx in indices:
            ligne = df.loc[idx]

            valide = bool(masque.loc[idx])
            cle = (ligne["chunk"], ligne["type_chunk"]) if valide else None

            # On conserve le chunk uniquement si les tokens
            # qui le composent sont consécutifs dans la source.
            if actif and (not valide or cle != (chunk_courant, type_courant)):
                chunks.add((
                    identifiant, debut, precedent,
                    chunk_courant, type_courant
                ))
                actif = False

            if valide and not actif:
                actif = True
                debut = ligne["_position"]
                chunk_courant = ligne["chunk"]
                type_courant = ligne["type_chunk"]

            if valide:
                precedent = ligne["_position"]

        if actif:
            chunks.add((
                identifiant, debut, precedent,
                chunk_courant, type_courant
            ))

    return chunks


@app.cell
def _(gold_dev, pred_gold_dev):
    chunks_gold = extraire_chunks_depuis_colonnes(gold_dev)
    chunks_pred = extraire_chunks_depuis_colonnes(pred_gold_dev)

    TP = len(chunks_gold & chunks_pred)
    FP = len(chunks_pred - chunks_gold)
    FN = len(chunks_gold - chunks_pred)

    precision = TP / (TP + FP) if TP + FP else 0
    rappel = TP / (TP + FN) if TP + FN else 0
    f1 = (
        2 * precision * rappel / (precision + rappel)
        if precision + rappel else 0
    )

    print(f"Vrais positifs (TP) : {TP}")
    print(f"Faux positifs (FP) : {FP}")
    print(f"Faux négatifs (FN) : {FN}")
    print(f"Précision : {precision:.3f}")
    print(f"Rappel    : {rappel:.3f}")
    print(f"F1        : {f1:.3f}")
    return FN, FP, TP, f1, precision, rappel


@app.cell(disabled=True, hide_code=True)
def _(FN, FP, TP, plt):
    mesures = {
        "TP": TP,
        "FP": FP,
        "FN": FN
    }

    plt.figure(figsize=(6, 4))
    plt.bar(mesures.keys(), mesures.values())
    plt.title("Évaluation des chunks exacts")
    plt.ylabel("Nombre de chunks")
    plt.tight_layout()
    plt.show()
    return


@app.cell(hide_code=True)
def _(FN, FP, TP, f1, mo, pd, precision, rappel):
    import plotly.express as px
    # Tableau des résultats
    df_resultats = pd.DataFrame({
        "Mesure": ["Vrais positifs (TP)", "Faux positifs (FP)", "Faux négatifs (FN)"],
        "Nombre": [TP, FP, FN]
    })

    # Graphique interactif
    fig = px.bar(
        df_resultats,
        x="Mesure",
        y="Nombre",
        text="Nombre",
        title="Évaluation des chunks exacts",
        labels={"Mesure": "Type de résultat", "Nombre": "Nombre de chunks"}
    )

    fig.update_traces(textposition="outside")
    fig.update_layout(
        yaxis=dict(rangemode="tozero"),
        xaxis_title="",
        showlegend=False
    )

    # Tableau des métriques
    df_metriques = pd.DataFrame({
        "Métrique": ["Précision", "Rappel", "F1-score"],
        "Valeur": [precision, rappel, f1]
    })

    mo.vstack([
        mo.md("### Résultats de l'évaluation des chunks"),
        mo.ui.table(df_resultats),
        mo.as_html(fig),
        mo.md("### Métriques de performance"),
        mo.ui.table(df_metriques)
    ])
    return df_metriques, df_resultats, fig


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Analyse des résultats

    | Mesure	| Niveau 1 : BILOU	| Niveau 2 : types chunks	| Niveau 3 : chunks exacts |
    | --- | --- | --- | --- |
    | Accuracy	| 91,14 %	| 89,67 %	| Non calculée |
    | Précision	| 90,73 %	| 88,50 %	| 74,90 % |
    | Rappel	| 90,06 %	| 89,24 %	| 77,10 % |
    | F-mesure	| 90,34 %	| 88,66 %	| 76,00 % |

    Ce tableau récapitule les résultats obtenus selon les trois niveaux d'évaluation. Nous constatons que le chunker est très performant pour l'étiquetage token par token avec un score global de +90%. Les erreurs restantes concernent les tokens intérieurs (`I`) et les chunks unitaires (`U`).

    Le F1 diminue de 1.68 point entre les niveaux 1 et 2, puis de 12.66 points entre les niveaux 2 et 3. La principale difficultée du chunker serait de reconstruire les chunks complets, plutôt que la classification des étiquettes.
    Pour la correspondance exacte des chunks, le chunker retrouve de nombreuses unités, mais les erreurs de frontières et de catégories empêchent une partie des cas.
    """)
    return


@app.cell(hide_code=True)
def _(accuracy_bilou, f1_bilou, mo, precision_bilou, rappel_bilou):
    mo.md(f"""
    ## 1. Evaluation des BILOU

    Le premier niveau compare, pour chaque token, l'étiquette attribuée par le chunker à l'étiquette de référence (*gold*). Les cinq catégories sont : 
    * **B** (_Begin_) : premier token d'un chunk multi-token.
    * **I** (_Inside_) : token intérieur d'un chunk.
    * **L** (_Last_) : dernier token d'un chunk multi-token.
    * **O** (_Outside_) : token situé hors de tout chunk.
    * **U** (_Unit_) : token constituant à lui seul un chunk.

    | Métrique | Score |
    |:---|---:|
    | Accuracy | {accuracy_bilou:.4f} |
    | Précision macro | {precision_bilou:.4f} |
    | Rappel macro | {rappel_bilou:.4f} |
    | F-mesure macro | {f1_bilou:.4f} |

    L'accuracy signifie que 9/10 tokens reçoivent une bonne étiquette. Le F1 donne une mesure synthétique de la précision et du rappel.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Les étiquettes bien reconnues

    Selon la matrice de confusion ci-dessus, les étiquettes `B` et `L` sont les mieux reconnues.
    * `B` : 93%
    * `L` : 91%

    Ces chiffres montre que le chunker repère correctement les frontières d'un chunk. C'est une bonne chose puisque la suite de notre analyse repose sur cela.

    Un petit bémole observé dans l'étiquetage de `L`, où 50 tokens réellement `L` sont prédit comme `U`. Ce qui signifie que le chunker reconnaît quelque fois une fin de segment syntaxique pour un seul chunk. De plus, une bonne reconnaissance individuelle des débuts et des fins ne garantit pas que ces deux frontières appartiennent au même chunk prédit.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### La fragilité de l'étiquette `I`

    Le rappel de `I` est de 81% contre 90% de précision. Cela signifie que le modèle retrouve la majorité des tokens intérieurs, mais environ 19% des `I` du gold sont manquants.

    L'unité interne (`I`) est souvent confondu avec l'étiquette de fin de chunk (`L`), le chunker tente des fois d'étiqueter comme fin (`B`) ou encore pour chunk unitaire (`U`). Cette confusion est interprétable via le rappel de `I` (81.3%), qui est nettement inférieur à `B` (0.93%).

    Cette erreur affecte les chunks composés de plus de deux tokens. Par exemple, si un token intérieur est classé `L`, le chunk se termine trop tôt ; s'il est classé `B`, un nouveau chunk est introduit sans en être un.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Les chunks unitaires `U` problématiques

    `U` obtient un F1 de 84%, une précision de 81% et un rappel de 86%.
    Le rappel est relativement supérieur à la précision, cela indique que le modèle trouve une bonne partie des chunks unitaire, mais annote trop souvent `U` à des endroits où l'étiquette n'est pas attendu.

    Il peut donc conduire à fragmenter un chunk multi-token en plusieurs unités ou créer des chunks unitaires incorrects. Or selon l'analyse plus haut, l'annotation `U` du chunker est fort probable de faire partie d'un token interne d'un chunk.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### L'étiquette `O`

    `O` obtient un rappel de 100%, une précision et un F1 de 99%. Le token faussé devrait être une erreur d'inattention lors de l'annotation gold (manuelle), car le chunker implémente les étiquettes `O` en groupe en fin de traitement.

    Même si le score de cette étiquette est excellent, cela ne signifie pas que les frontières sont correctement délimitées par `O`. Au contraire, dans le corpus d'analyse, pas mal de chunk débordde sur le burst (segment de frappe enregistré entre des pauses longues) suivant. De ce fait, il n'est pas possible de dire qu'un tag `O` représente clairement le début ou la fin d'un chunk.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Selon la matrice de confusion
    """)
    return


@app.cell(hide_code=True)
def _(cm_bilou, fig_confusion_matrix, labels_bilou):
    fig_confusion_matrix(cm_bilou, labels_bilou, title="Matrice de confusion - BILOU")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    La matrice confirme que les confusions sont concentrées sur certaines étiquettes.
    * `B` $\rightarrow$ `U` : 36 cas
    * `L` $\rightarrow$ `U` : 50 cas

    $\Rightarrow$ Des débuts et fins de chunks sont annotés comme unitaires par le chunker. Cette confusion est importante car elle peut affecter la reconstruction des frontières.

    * `I` $\rightarrow$ `L` : 31 cas

    $\Rightarrow$ Certains tokens intérieurs sont interprétés comme des fins de chunks. Ainsi, les chunks finissent plus tôt que voulu et de nouveaux chunks s'ajoutent. Les multi-tokens sont coupés en deux voire plus.

    * `U` $\rightarrow$ `L` : 29 cas
    * `U` $\rightarrow$ `B` : 28 cas

    $\Rightarrow$ Les unités sont parfois interprétées comme des parties de chunks multi-token.

    Ces confusions peuvent être une explications plausibles de la baisse du F1 de la correspondance des chunks exacts.
    """)
    return


@app.cell(hide_code=True)
def _(accuracy_type, f1_type, mo, precision_type, rappel_type):
    mo.md(f"""
    ## 2. Les types de chunks

    Le deuxième niveau évalue les catégories syntaxiques, telles que : 
    * NP (_Noun Phrase_)
    * VP (_Verb Phrase_)
    * PP (_Prepositional Phrase_)
    * AP (_Adjective Phrase_)
    * ADVP (_Adverb Phrase_)
    * CONJ (_Conjunction_)
    * UNKNOWN le "fourre-tout"
    * <PAUSE\>, <SUPPR\>, <SPACE\> les catégories spéciaux

    | Métrique | Score |
    |:---|---:|
    | Accuracy | {accuracy_type:.4f} |
    | Précision macro | {precision_type:.4f} |
    | Rappel macro | {rappel_type:.4f} |
    | F-mesure macro | {f1_type:.4f} |

    Le chunker reconnaît correctement une grande partie des types de chunks. La différence de 1.68 poibt de F1 avec le niveau BILOU est relativement limitée. Néanmoins, certaines classes sont plus difficiles que d'autres.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Les catégories les mieux reconnues

    #### <PAUSE\>, <SUPPR\> et <SPACE\>

    Les catégories techniques <PAUSE\>, <SPACE\> et <SUPPR\> sont parfaitement reconnues. Cela s'explique par le copier-coller de ces données du corpus annoté par le chunker au corpus annoté manuellement. Ces étiquettes sont plus significative sur d'autres sujets d'analyse que celui qui nous intéresse maintenant. De plus, l'automatisme implémenté dans le chunker permettait de choisir correctement entre ces trois étiquettes selon la colonnes `charBurst` et `burst` du corpus d'origine.

    C'était aussi un moyen d'avoir le moins de cellule vide et sans signification dans notre corpus après traitement.

    #### VP -- groupes verbaux

    F1 = 94%

    C'est la meilleure performance parmi les principales catégories syntaxiques. La précision de 94% et le rappel de 95% montrent que le modèle reconnaît bien les VP présents dans le corpus et produit relativement peu de VP erronés.

    #### PP -- groupe prépositionnels

    F1 = 89%

    C'est la catégorie la plus importante parmi les autres groupes syntaxiques (843 occurrences). Une précision de 91% et le rappel de 87% montrent que les PP sont globalement bien reconnus, mais qu'une partie des PP du gold ne sont pas trouvée.

    #### NP -- groupes nominaux

    F1 = 84%

    Le rappel (87%) est supérieur à la précision (80%). Le chunker retrouve une grande partie des NP mais sur-annote des NP. Cette différence peut être traduit par des confusions entre groupes nominaux et d'autres catégories syntaxiques, des frontières incorrectes ou encore simplement une mauvaise étiquetage du POSTagger.

    Cette partie sera détaillé avec la matrice de confusion plus loin.

    #### CONJ -- conjonctions

    F1 : 84%

    La précision atteint 95% mais le rappel assez bas en comparaison (75%). Le modèle est assez fiable pour annoté les CONJ, mais il manque environ un quart des occurrences gold. Ce manque s'explique par un nombre de locutions conjonctives non intégrées dans la ressource du chunker. Celles-ci ont été repéré lors de l'annotation manuelle et non lors de la construction du chunker.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Les catégories plus difficiles

    #### AP -- groupes adjectivaux

    F1 = 64%

    C'est la catégorie syntaxique la plus difficile parmi les classes principales. Sa précision de 0.57 signifie que 43% des annotations du chunker sont erronées. Son rappel de 0.74 indique que le modèle retrouve environ les trois quarts des AP du gold.

    Cette catégorie ne compte que 38 occurrences gold. Son faible support rend l'estimation plus sensible à quelques erreurs supplémentaires. De plus, pendant l'annotation manuelle, certains AP peuvent être absorbé dans d'autres groupes syntaxiques, à la différence du chunker qui suit les règles à la lettre.

    #### UNKNOWN

    F1 = 70%

    La précision (0.69) et le rappel (0.70) sont modérés. Cette classe regroupe des cas hétérogènes. Selon l'annotation du POSTagger et l'interprétation de l'humain, cette classe peut beaucoup différer. Comme il regroupe tout ce dont il semble impossible de catégoriser, il est fort probable que le taux de `UNKNOWN` du gold est plus importante qu'au chunker.


    #### ADVP -- groupes adverbiaux

    F1 = 80%

    Le rappel (0.84) dépasse la précision (0.76). C'est-à-dire que le chunker retrouve relativement bien les `ADVP` mais qu'il en sur-annote un grand nombre de cas.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Selon la matrice de confusion
    """)
    return


@app.cell(hide_code=True)
def _(cm_type, fig_confusion_matrix, labels_type):
    # Figure
    fig_confusion_matrix(cm_type, labels_type, title="Matrice de confusion - Types chunks")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Les principales confusions observées dans la matrice ci-dessus :
    * `PP` $\rightarrow$ `NP` : 85 cas.

    $\Rightarrow$ C'est une confusion importante entre deux catégories syntaxiques fréquentes. Elle peut provenir d'une différence de typage, d'une erreur de combinaison ou d'une combinaison des deux cas.

    * `NP` $\rightarrow$ `PP` : 42 cas.

    $\Rightarrow$ La confusion fonctionne dans les deux sens, mêmes si les effectifs sont différents.

    * `ADVP` $\rightarrow$ `AP` : 4 cas.
    * `AP` $\rightarrow$ `ADVP` : 2 cas.

    $\Rightarrow$ Ces confusions existent, mais ne suffisent pas à expliquer à elles seules le faible F1 de AP.

    * `CONJ` $\rightarrow$ `ADVP` : 12 cas.

    $\Rightarrow$ Ce type d'erreur contribue à la perte de rappel de `CONJ`.

    * `UNKNOWN` $\rightarrow$ `NP` : 9 cas.
    * `UNKNOWN` $\rightarrow$ `PP` : 7 cas.

    $\Rightarrow$ La classe `UNKNWON` se confond avec des catégories syntaxiques plus courantes. Cela peut être du à un mauvais découpage des chunks.

    * `VP` $\rightarrow$ `NP` : 4 cas.
    * `VP` $\rightarrow$ `PP` : 8 cas

    $\Rightarrow$ Les erreurs de typage des `VP` restent limitées relativement à leur support.

    La confusion NP-PP peut être du à la différence d'interprétation de certains ADP, qui selon le contexte peut être déterminant ou préposition. Le rôle du POSTagger est important dans cette partie.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Le faible support de NUM a permit un score parfait. Dans l'échantillon choisi, cette catégories était très peu présente (seulement 1 occurrence).

    Pour conclure, le modèle reconnaît bien les catégories syntaxiques fréquentes, en particulier VP et PP. Ses principales difficultés concernent AP, UNKNOWN et certaines confusions entre NP et PP. Ces erreurs peuvent contribuer à la dégradation des chunks exacts, mais leurs effets précis ne peuvent pas être déduits des seules matrices de confusion.
    """)
    return


@app.cell(hide_code=True)
def _(df_resultats, fig, mo):
    mo.md(f"""
    ## 3. Les chunks exacts

    {mo.ui.table(df_resultats)}
    {mo.as_html(fig)}
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Les vraies positifs

    Les 1082 TP correspondent aux chunks prédits qui satisfont exactement le critère de correspondance avec le chunk gold.

    Pour qu'un chunk soit considéré comme exact, il faut normalement que les conditions définies par le protocole soient toutes satisfaites :
    1. même token de début
    2. même token de fin
    3. même type syntaxique
    4. même unité d'évaluation, notamment concernant les frontières entre bursts.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Les faux positifs

    Les 362 FP correpondent à des chunks prédits qui ne trouvent pas de correspondance exacte dans la référence.

    Plusieurs situations peuvent produire des FP :
    * un chunk est créé alors qu'aucun chunk gold ne correspond à cette portion
    * les frontières du chunk prédit sont trop courtes ou trop longues
    * le type syntaxique est incorrect
    * un chunk est fragmenté en plusieurs chunks prédits
    * une règle d'alignement entre bursts ne permet pas d'apparier la prédiction et la référence

    Ce nombre de FP signifie que le modèle produit des chunks non validés par le gold que ne laisserait penser sa seule accuracy token par token (niveau 1)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Les faux négatifs

    Les 322 FN représentent des chunks gold qui n'ont pas été retrouvés.

    Un chunk peut être compté comme FN même si une grande partie de ses tokens est correctement prédite. Par exemple un groupe nominal peut être bien identifié dans son contenu, mais ne pas être reconnu comme un seul chunk parce que son dernier token est mal étiqueté.

    Il est important de noter qu'une seule erreur de segmentation peut engendrer simultanément plusieurs conséquences. Par exemple, un chunk gold peut être manqué et plusieurs chunks prédits à sa place peuvent être incorrects. Les 362 FP et 322 FN ne correspondent donc pas nécessairement à 684 erreurs indépendantes.

    De plus, avant de procéder à l'évaluation, nous avons décidé de diviser le corpus gold en 30-70 pour pouvoir garder un échantillon si des modifications seront apportées aux règles syntaxiques en vu de résultats catastrophiques de la première évaluation. Cette division s'est fait un peu aléatoire dans le corpus gold. Pour avoir un bout d'échantillon de toutes les thématiques abordées (médecine, alcool, transport en commun...) et une extraction équitable de toutes les `ID` (F+/F-, P+/P-, R+/R-). Il soit possible que des chunks du corpus annoté par le chunker soit coupé en deux, puisque la séparation s'est basée sur le corpus gold.
    """)
    return


@app.cell(hide_code=True)
def _(df_metriques, mo):
    mo.md(f"""
    ### Une précision légèrement inférieur au rappel

    {mo.ui.table(df_metriques)}

    La précision est de 74,9%, tandis que le rappel atteint 77,1%. L'écart est de 2.2 points.

    Le modèle retrouve donc une proportion légèrement plus importante des chunks gold qu'il ne produit de chunks validés. Il existe un déséquilibre modéré en faveur du rappel : les prédictions non validées sont un peu plus nombreuses que les chunks gold manqués.
    * 1444 chunks ont été prédits, soit 1082+362 (FP)
    * 1404 chunks gold sont à retrouver, soit 1082+322 (FN)
    * 1082 correspondent exactement

    Sur la base de ces comptes, environ 25,1% des chunks prédits ne sont pas des correspondances exactes, et environ 22,9% des chunks gold ne sont pas retrouvés exactement.

    Ces chiffres ne signifient pas nécessairement que 25,1% des groupes syntaxiques sont totalement dépourvus d'information correcte : certains peuvent présenter un contenu largement juste, mais des frontières ou un type erronés.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Limites et conclusion

    ### Limites

    Comme nous avons pu l'observer lors de l'analyse, le score d'accuracy du niveau 1 (BILOU) est très élevé, cependant, ce score peut être influencée par la distribution des classes. L'étiquette `O` atteint un F1 de 0.99, ce qui contribue favorablement au score global.

    De plus, en raison d'une extraction aléatoire du corpus gold, le support des classes est inégal. Les catégories fréquentes comme `PP` et `NP` pèsent beaucoup plus dans les performances globales que `NUM` ou `SPACE`. Les scores parfaits de certaines classes rares ne doivent pas être interprétés comme une garantie de généralisation. Mais aussi, le score faible de classe ambiguë est tout à fait explicable et raisonable. La compréhension du texte par l'humain est très divers comparé aux chunker qui suit des règles quelque fois incomplète.

    Enfin, l'évaluation du niveau 3 est très sensible à la moindre erreur. Ce qui explique son taux plus faible que les deux autres niveaux.

    ### Conclusion

    Les résultats montrent que le chunker reconnaît correctement la majorité des étiquettes BILOU et les catégories syntaxiques, avec des performances globales proches de 90% sur les deux premiers niveaux. Les catégories `VP` et `PP` sont particulièrement bien reconnues, tandis que les étiquettes `I` et `U`, les groupes `AP` et l'étiquette `UNKNOWN` présentent davantage de difficultés.

    En revanche, le F1 exact de 76% révèle une différence notable entre la reconnaissance des éléments locaux et la reconstruction des chunks complets. Ce résultat indique que la qualité finale de la segmentation reste inférieure à ce que suggèrent les scores token par token et par type.

    L'hypothèse prioritaire est celle des erreurs de frontières, notamment lorsque les chunks traversent plusieurs bursts. Les confusions BILOU observées et les difficultés de classification de certaines catégories peuvent également contribuer à cet écart. Mais aussi, il soit possible que la division de l'échantillon gold a empiré le corpus d'évaluation. Cependant, les résultats actuels ne permettent pas d'attribuer une proportion précise à la baisse à chacun de ces facteurs.
    """)
    return


if __name__ == "__main__":
    app.run()
