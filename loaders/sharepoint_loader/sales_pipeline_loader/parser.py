import io
import logging
from datetime import datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

SHEET_NAME = "Base ouverte"
HEADER_ROW = 2

_RENAMES = {
    "Opportunité":             "opportunity_name",
    "Vendeur":                 "salesperson",
    "Pays":                    "country",
    "Date de clôture prévue":  "expected_close_date",
    "Offre commerciale":       "contract_type",
    "Valeur considérée":       "target_value",
    "Secteur d'activité 2":    "sector",
}

_KEEP = list(_RENAMES.values())


def _read_sheet(file_content: io.BytesIO) -> Optional[pd.DataFrame]:
    file_content.seek(0)
    xl = pd.ExcelFile(file_content)
    if SHEET_NAME not in xl.sheet_names:
        logger.warning("Sheet '%s' not found. Available: %s", SHEET_NAME, xl.sheet_names)
        return None
    file_content.seek(0)
    return pd.read_excel(file_content, sheet_name=SHEET_NAME, header=HEADER_ROW)


def _billing_target_column_name(month: datetime) -> str:
    return f"billing_target_{month.year}_{month.month:02d}"


def parse_pipeline(file_content: io.BytesIO) -> Optional[pd.DataFrame]:
    df = _read_sheet(file_content)
    if df is None:
        return None

    # Billing targets: one column per month (K to AH), header = 1st of the month.
    month_cols = [c for c in df.columns if isinstance(c, datetime)]
    billing_renames = {c: _billing_target_column_name(c) for c in month_cols}

    df = df.rename(columns=_RENAMES)

    missing = [c for c in _KEEP if c not in df.columns]
    if missing:
        logger.warning("Missing columns: %s", missing)

    df = df[[c for c in _KEEP if c in df.columns] + month_cols].copy()
    df = df.rename(columns=billing_renames)
    df = df[df["opportunity_name"].notna()].reset_index(drop=True)

    df["expected_close_date"] = pd.to_datetime(df["expected_close_date"], errors="coerce")
    df["target_value"] = pd.to_numeric(df["target_value"], errors="coerce")
    for col in billing_renames.values():
        df[col] = pd.to_numeric(df[col], errors="coerce")

    logger.info("sales_pipeline: %d rows extracted (%d monthly billing target columns)", len(df), len(month_cols))
    return df
