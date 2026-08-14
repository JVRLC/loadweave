"""Supabase REST helpers for sample_results upsert."""

from __future__ import annotations

import json
import logging
import os

import pandas as pd
import requests

logger = logging.getLogger(__name__)

TABLE_NAME = "sample_results"
BATCH_SIZE = 50


def _headers() -> dict:
    api_key = os.getenv("SUPABASE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing SUPABASE_API_KEY")
    return {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _base_url() -> str:
    url = os.getenv("SUPABASE_URL")
    if not url:
        raise RuntimeError("Missing SUPABASE_URL")
    return url.rstrip("/")


def fetch_table(table_name: str) -> pd.DataFrame:
    url = f"{_base_url()}/rest/v1/{table_name}?select=*"
    response = requests.get(url, headers=_headers())
    if response.status_code == 200:
        data = response.json()
        logger.info("Successfully fetched %s with %d records", table_name, len(data))
        return pd.DataFrame(data)
    logger.error(
        "Error fetching %s: %s - %s", table_name, response.status_code, response.text
    )
    return pd.DataFrame()


def map_lot_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Resolve Code générique / external_id to lots.id (case-insensitive)."""
    logger.info("Fetching existing data from Supabase...")
    df_lots = fetch_table("lots")
    if df_lots.empty:
        logger.warning("No lots found in Supabase — lot_id mapping will be empty")
        out = df.copy()
        out["lot_id"] = None
        return out

    # Lowercase key → (lot id, canonical external_id as stored in Supabase)
    lot_id_map = {
        str(row["external_id"]).lower(): (row["id"], row["external_id"])
        for _, row in df_lots.iterrows()
    }
    out = df.copy()
    keys = out["external_id"].astype(str).str.lower()
    mapped = keys.map(lot_id_map)
    out["lot_id"] = mapped.apply(lambda v: v[0] if isinstance(v, tuple) else None)
    # Prefer Supabase casing (e.g. CSM7XX vs CSM7xx)
    out["external_id"] = [
        v[1] if isinstance(v, tuple) else ext
        for v, ext in zip(mapped, out["external_id"])
    ]
    if "external_id_usable" in out.columns:
        out["external_id_usable"] = (
            out["external_id"].astype(str) + "-" + out.index.astype(str)
        )

    n_ok = out["lot_id"].notna().sum()
    n_miss = out["lot_id"].isna().sum()
    logger.info(
        "Mapped %d/%d rows to lots (%d lot codes in Supabase, %d unmatched rows)",
        n_ok,
        len(out),
        len(lot_id_map),
        n_miss,
    )
    if n_miss:
        missing_codes = sorted(out.loc[out["lot_id"].isna(), "external_id"].astype(str).unique())
        logger.warning(
            "Unmatched external_id codes (%d): %s",
            len(missing_codes),
            missing_codes[:30],
        )
    return out


def upsert_sample_results(df: pd.DataFrame) -> int:
    """Upsert rows into sample_results on external_id_usable. Returns row count sent."""
    headers = _headers()
    headers["Prefer"] = "resolution=merge-duplicates"

    df_final = df[
        [
            "sampling_date",
            "result",
            "F",
            "M",
            "m",
            "a",
            "A",
            "lot_id",
            "external_id",
            "quality_control",
            "external_id_usable",
        ]
    ].dropna(subset=["lot_id"])

    if df_final.empty:
        logger.warning("No rows with resolvable lot_id — nothing to upload")
        return 0

    df_final = df_final.copy()
    df_final["lot_id"] = df_final["lot_id"].astype(int)
    df_final["external_id"] = df_final["external_id"].astype(str)

    rows = df_final.to_dict(orient="records")
    total_batches = (len(rows) + BATCH_SIZE - 1) // BATCH_SIZE
    logger.info(
        "Uploading %d records in %d batches of %d",
        len(rows),
        total_batches,
        BATCH_SIZE,
    )

    url = f"{_base_url()}/rest/v1/{TABLE_NAME}?on_conflict=external_id_usable"
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        logger.info("Sending batch %d/%d (%d records)", batch_num, total_batches, len(batch))

        response = requests.post(url, headers=headers, data=json.dumps(batch))
        if response.status_code not in (200, 201, 204):
            logger.error(
                "Error in batch %d: %s - %s",
                batch_num,
                response.status_code,
                response.text,
            )
        else:
            logger.info("Batch %d/%d inserted or updated successfully.", batch_num, total_batches)

    return len(rows)
