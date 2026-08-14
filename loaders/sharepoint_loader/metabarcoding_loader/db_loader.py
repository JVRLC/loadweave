import gc
from datetime import datetime

import pandas as pd
from sqlalchemy import text
from dotenv import load_dotenv
from loaders.db import get_engine
from loaders.sharepoint_loader.shared.db_loader import _prepare_dataframe

load_dotenv()

SCHEMA = "raw"



def batch_already_loaded(batch_id: str) -> bool:
    """Return True if this batch_id is already in raw.metag_batch."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT 1 FROM raw.metag_batch WHERE batch_id = :b"),
                {"b": batch_id},
            ).fetchone()
            return row is not None
    except Exception:
        return False
    finally:
        engine.dispose()


def upsert_batch(batch_info: dict):
    engine = get_engine()
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO raw.metag_batch
                        (batch_id, seq_date, seq_range_start, seq_range_end,
                         prestataire, otu_table_path, _loaded_at)
                    VALUES
                        (:batch_id, :seq_date, :seq_range_start, :seq_range_end,
                         :prestataire, :otu_table_path, :loaded_at)
                    ON CONFLICT (batch_id) DO UPDATE SET
                        otu_table_path = EXCLUDED.otu_table_path,
                        _loaded_at = EXCLUDED._loaded_at
                """),
                {**batch_info, "loaded_at": datetime.now()},
            )
        print(f"✓ Batch upserted: {batch_info['batch_id']}")
    finally:
        engine.dispose()


def upsert_samples(samples: list[dict]):
    """Insert or update rows in raw.metag_sample."""
    if not samples:
        return
    engine = get_engine()
    try:
        with engine.begin() as conn:
            for s in samples:
                s.setdefault("_loaded_at", datetime.now())
                conn.execute(
                    text("""
                        INSERT INTO raw.metag_sample
                            (sample_id, batch_id, client_code, product_type,
                             culture, localisation, country,
                             latitude, longitude, date_envoi, date_reception,
                             sample_type, _loaded_at)
                        VALUES
                            (:sample_id, :batch_id, :client_code, :product_type,
                             :culture, :localisation, :country,
                             :latitude, :longitude, :date_envoi, :date_reception,
                             :sample_type, :_loaded_at)
                        ON CONFLICT (sample_id) DO UPDATE SET
                            batch_id         = COALESCE(EXCLUDED.batch_id, raw.metag_sample.batch_id),
                            client_code      = COALESCE(EXCLUDED.client_code, raw.metag_sample.client_code),
                            product_type     = COALESCE(EXCLUDED.product_type, raw.metag_sample.product_type),
                            culture          = COALESCE(EXCLUDED.culture, raw.metag_sample.culture),
                            localisation     = COALESCE(EXCLUDED.localisation, raw.metag_sample.localisation),
                            date_envoi       = COALESCE(EXCLUDED.date_envoi, raw.metag_sample.date_envoi),
                            date_reception   = COALESCE(EXCLUDED.date_reception, raw.metag_sample.date_reception),
                            sample_type      = COALESCE(EXCLUDED.sample_type, raw.metag_sample.sample_type),
                            _loaded_at       = EXCLUDED._loaded_at
                    """),
                    s,
                )
        print(f"✓ {len(samples)} samples upserted")
    finally:
        engine.dispose()


def upsert_sample_metadata(updates: list[dict]):
    """Update agronomic fields in raw.metag_sample from REF file, batched to avoid SSL issues."""
    if not updates:
        return
    _BATCH = 100
    sql = text("""
        UPDATE raw.metag_sample SET
            client_code    = CASE WHEN :client_code    IS NOT NULL THEN :client_code    ELSE client_code    END,
            product_type   = CASE WHEN :product_type   IS NOT NULL THEN :product_type   ELSE product_type   END,
            culture        = CASE WHEN :culture        IS NOT NULL THEN :culture        ELSE culture        END,
            sample_type    = CASE WHEN :sample_type    IS NOT NULL THEN :sample_type    ELSE sample_type    END,
            latitude       = CASE WHEN :latitude       IS NOT NULL THEN :latitude       ELSE latitude       END,
            longitude      = CASE WHEN :longitude      IS NOT NULL THEN :longitude      ELSE longitude      END,
            localisation   = CASE WHEN :localisation   IS NOT NULL THEN :localisation   ELSE localisation   END,
            date_envoi     = CASE WHEN :date_envoi     IS NOT NULL THEN :date_envoi     ELSE date_envoi     END,
            date_reception = CASE WHEN :date_reception IS NOT NULL THEN :date_reception ELSE date_reception END,
            _loaded_at     = NOW()
        WHERE sample_id = :sample_id
    """)
    engine = get_engine()
    total = 0
    try:
        for i in range(0, len(updates), _BATCH):
            batch = updates[i : i + _BATCH]
            with engine.begin() as conn:
                for u in batch:
                    conn.execute(sql, u)
            total += len(batch)
        print(f"✓ {total} samples enrichis depuis REF SEQ")
    finally:
        engine.dispose()


def load_otu_abundance(df: pd.DataFrame, batch_id: str, chunk_size: int = 500):
    """
    Bulk-insert OTU abundance rows.
    Uses INSERT ... ON CONFLICT DO NOTHING to stay idempotent.
    """
    engine = get_engine()
    df = df.copy()
    df["batch_id"] = batch_id
    df = _prepare_dataframe(df)

    columns = [
        "sample_id", "batch_id", "otu_id", "taxonomy_raw",
        "taxon_kingdom", "taxon_phylum", "taxon_class", "taxon_order",
        "taxon_family", "taxon_genus", "taxon_species",
        "abundance_absolute", "abundance_relative", "is_ama", "is_pathogen",
        "_loaded_at", "_source",
    ]
    df = df[[c for c in columns if c in df.columns]]

    total = len(df)
    inserted = 0
    try:
        for i in range(0, total, chunk_size):
            chunk = df.iloc[i: i + chunk_size]
            chunk.to_sql(
                name="metag_otu_abundance",
                con=engine,
                schema=SCHEMA,
                if_exists="append",
                index=False,
                method="multi",
            )
            inserted += len(chunk)
            del chunk
            gc.collect()
        print(f"✓ {inserted}/{total} OTU rows loaded for batch {batch_id}")
    finally:
        engine.dispose()
    return inserted
