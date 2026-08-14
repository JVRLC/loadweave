import re
import logging
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

REF_FILE_PATH = (
    "03_R&D INNOV/30_LABORATOIRE ANALYSES CONTRATS CQ"
    "/03_Métagénomique - Data & Traçabilité"
    "/Procédure d'envoi - Traçabilité/3-REF SEQ IGATECH.xlsx"
)

_TYPE_MAP = {
    "sol":      "sol",
    "sol ":     "sol",
    "racine":   "racines",
    "racines":  "racines",
    "prod":     "production",
    "mix":      "mix",
    "substrat": "substrat",
    "broyat":   "broyat",
    "autre":    "autre",
}

_SEQ_RE = re.compile(r"SEQ-?(\d+)", re.IGNORECASE)


def _normalize_seq_ref(value: str) -> str | None:
    """'SEQ021', 'SEQ-112', 'ID2985-1-SEQ021' → 'SEQ021' / 'SEQ112'."""
    m = _SEQ_RE.search(str(value))
    if not m:
        return None
    num = int(m.group(1))
    return f"SEQ{num:03d}" if num < 1000 else f"SEQ{num}"


def extract_seq_ref_from_sample_id(sample_id: str) -> str | None:

    return _normalize_seq_ref(sample_id)


def build_ref_lookup(file_content) -> dict[str, dict]:
    df = pd.read_excel(file_content, sheet_name="Feuil1")
    df = df[df["Réf IgaTech"].notna()].copy()

    lookup = {}
    for _, row in df.iterrows():
        seq_ref = _normalize_seq_ref(str(row["Réf IgaTech"]).strip())
        if not seq_ref:
            continue
        sample_type_raw = str(row.get("Type", "") or "").strip().lower()
        lat = row.get("Latitude_deci")
        lon = row.get("Longitude_deci")
        commentaire = row.get("Commentaire")
        envoi = row.get("Envoi")
        reception = row.get("Reception")
        lookup[seq_ref] = {
            "client_code":    str(row.get("Code client / projet") or "").strip() or None,
            "culture":        str(row.get("Plante") or "").strip() or None,
            "product_type":   sample_type_raw or None,
            "sample_type":    _TYPE_MAP.get(sample_type_raw),
            "latitude":       float(lat) if pd.notna(lat) else None,
            "longitude":      float(lon) if pd.notna(lon) else None,
            "localisation":   str(commentaire).strip() if pd.notna(commentaire) else None,
            "date_envoi":     envoi.date() if pd.notna(envoi) else None,
            "date_reception": reception.date() if pd.notna(reception) else None,
        }
    logger.info("REF lookup built: %d entries", len(lookup))
    return lookup


def lookup_sample_meta(sample_id: str, ref_lookup: dict) -> dict:
    """Retourne les métadonnées REF pour un sample_id, ou un dict vide."""
    seq_ref = extract_seq_ref_from_sample_id(sample_id)
    if not seq_ref:
        return {}
    return ref_lookup.get(seq_ref, {})


def enrich_all_samples(ref_lookup: dict):
    from loaders.sharepoint_loader.metabarcoding_loader.db_loader import (
        upsert_sample_metadata,
    )
    from loaders.db import get_engine
    from sqlalchemy import text

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT sample_id FROM raw.metag_sample")).fetchall()
    engine.dispose()

    sample_ids = [r[0] for r in rows]
    logger.info("Enriching %d samples from REF lookup...", len(sample_ids))

    updates = []
    for sample_id in sample_ids:
        meta = lookup_sample_meta(sample_id, ref_lookup)
        if meta:
            updates.append({"sample_id": sample_id, **meta})

    matched = len(updates)
    logger.info("Matched %d/%d samples with REF data", matched, len(sample_ids))
    if updates:
        upsert_sample_metadata(updates)
    if len(sample_ids) - matched:
        logger.warning("%d samples had no match in REF file", len(sample_ids) - matched)


def run():
    from loaders.sharepoint_loader.config import SHAREPOINT_CONFIG
    from loaders.sharepoint_loader.shared.client import SharePointClient

    client = SharePointClient.from_config(SHAREPOINT_CONFIG)
    client.authenticate()

    logger.info("Downloading REF file...")
    file_content = client.download_file(REF_FILE_PATH)
    ref_lookup = build_ref_lookup(file_content)
    enrich_all_samples(ref_lookup)


if __name__ == "__main__":
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run()
