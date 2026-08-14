"""Excel cleaning and row transforms for sample results."""

from __future__ import annotations

import logging
import re

import pandas as pd

logger = logging.getLogger(__name__)

# Expected header columns (must match the Excel layout exactly).
EXPECTED_COLUMNS = [
    "Mix ou Contrat",
    "Nom projet",
    "Plan expérimentation",
    "Lot",
    "Clé",
    "Echantillon",
    "Tamis granulométrie",
    "Etape de contrôle qualité ",
    "Date création ech",
    "Semaine ",
    "Mois",
    "Année",
    'OUI si analyses terminées N/A si ne sera pas analysé "vide" si reste à analyser',
    "Opérateur création ech",
    "Référent /analyses",
    "Substrat / Racines / Broyat",
    "Serre ",
    "Commentaire",
    "Indice de Biodiversité (Dénombremt)",
    "Taux de Mycorhization (Coloration) ",
    "Poids racines (poids frais et/ou poids sec)",
    "Dosage phosphate",
    "Autres (à préciser)",
    "Date Dénombrement",
    "Semaine 2",
    "Mois 2",
    "Année 2",
    "Résultat (spores/g)",
    "COEFF",
    "Valeur finale (spores/g)",
    "Date de lecture",
    "semaine 3",
    "MOIS 3",
    "ANNEE 3 ",
    "F",
    "M",
    "m ",
    "a",
    "A ",
]

QUALITY_CONTROL_MAPPING = {
    "S+6": "S_6",
    "S+8": "S_8",
    "S+12": "S_12",
    "S+24": "S_24",
    "S+14": "S_14",
    "S+20": "S_20",
    "S+11": "S_11",
    "S+5": "S_5",
    "S+4": "S_4",
    "S+16": "S_16",
    "FORMULE": "FORMULE",
    "CQ STRESS": "CQ_STRESS",
    "CQ NO STRESS": "CQ_NO_STRESS",
    "Indice bio sol": "INDICE_BIO_SOL",
}

SHEET_NAME = "échantillons et résultats"
MIN_SAMPLING_DATE = "2025-01-01"


def clean_excel(raw: pd.DataFrame) -> pd.DataFrame:
    """Locate the real header row and return a clean DataFrame."""
    logger.info("Cleaning Excel data structure...")
    real_col = raw.columns.tolist()
    index = 0
    while EXPECTED_COLUMNS != [i for i in real_col if isinstance(i, str)]:
        index += 1
        if index >= len(raw):
            raise ValueError("Could not locate expected header row in Excel sheet")
        real_col = raw.iloc[index].tolist()

    df = raw.copy()
    df.columns = real_col
    df = df.iloc[index + 1 :]
    df = df.loc[:, df.columns.notna()]
    logger.info(
        "Data cleaned. Found header at row %d, data starts at row %d",
        index,
        index + 1,
    )
    return df


def generate_code(row: pd.Series) -> str | None:
    """Build a lot external_id matching Supabase `lots.external_id`.

    Format: ``{product:<6 x-pad>}#D{dd}-L{dd}``
    e.g. MIX CRR2 → ``CRR2xx#…``, MIX AVC → ``AVCxxx#…``,
    MIX LHA9-M → ``LHA9Mx#…`` (single-letter plan suffix only).
    """
    mix_contract = str(row["Mix ou Contrat"])
    exp_plan = str(row["Plan expérimentation"])
    lot = str(row["Lot"])

    if "mix" not in mix_contract.lower():
        return None

    # Product token after MIX: letters+digits, optional single-letter suffix (-M / -A).
    # Multi-letter variants (CRR2-AST, CRR2-MAR) are ignored — they share CRR2xx.
    match_mix = re.search(
        r"MIX\s*([A-Za-z]+\d*)(?:-([A-Za-z])(?![A-Za-z]))?",
        exp_plan,
        re.IGNORECASE,
    )
    if match_mix:
        product = ((match_mix.group(1) or "") + (match_mix.group(2) or "")).upper()
    else:
        product = ""

    part1 = product.ljust(6, "x")[:6]

    match_d = re.search(r"D\s*(\d+)", lot, re.IGNORECASE)
    part2 = f"D{int(match_d.group(1)):02d}" if match_d else "D00"

    match_l = re.search(r"lot\s*(\d+)", lot, re.IGNORECASE)
    part3 = f"L{int(match_l.group(1)):02d}" if match_l else "L00"

    return f"{part1}#{part2}-{part3}"


def transform_quality_control(value) -> str:
    return QUALITY_CONTROL_MAPPING.get(str(value).strip(), str(value).strip())


def to_float(x):
    try:
        if isinstance(x, (int, float)):
            return float(x) if x >= 0 else -1
        x = float(str(x).replace(",", "."))
        return x if x >= 0 else -1
    except (TypeError, ValueError):
        return None


def prepare_records(df: pd.DataFrame) -> pd.DataFrame:
    """Filter Mix rows, map columns, and prepare the upsert payload."""
    logger.info("Generating generic codes for data...")
    df = df.copy()
    df["Code générique"] = df.apply(generate_code, axis=1)

    df_mix = pd.concat(
        [
            df[df["Mix ou Contrat"] == "Mix"],
            df[df["Mix ou Contrat"] == "MIX"],
        ]
    )
    logger.info("Filtered to %d Mix records", len(df_mix))

    out = df_mix[
        [
            "Date création ech",
            "Résultat (spores/g)",
            "F",
            "M",
            "m ",
            "a",
            "A ",
            "Lot",
            "Opérateur création ech",
            "Référent /analyses",
            "Code générique",
            "Etape de contrôle qualité ",
        ]
    ].copy()

    logger.info("Formatting dates and filtering data...")
    out["Date création ech"] = pd.to_datetime(
        out["Date création ech"], dayfirst=True
    ).dt.strftime("%Y-%m-%d")
    out = out[out["Date création ech"] > MIN_SAMPLING_DATE]
    logger.info("After date filtering: %d records", len(out))

    out["Etape de contrôle qualité "] = out["Etape de contrôle qualité "].apply(
        transform_quality_control
    )

    out.rename(
        columns={
            "Date création ech": "sampling_date",
            "Résultat (spores/g)": "result",
            "Etape de contrôle qualité ": "quality_control",
            "Code générique": "external_id",
            "m ": "m",
            "A ": "A",
        },
        inplace=True,
    )

    for col in ["result", "F", "M", "m", "a", "A"]:
        out[col] = out[col].apply(to_float)

    out["external_id_usable"] = out["external_id"] + "-" + out.index.astype(str)
    return out
