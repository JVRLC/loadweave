import logging
from datetime import datetime
from sqlalchemy import text
import pandas as pd
from dotenv import load_dotenv
from loaders.db import get_engine

load_dotenv()

logger = logging.getLogger(__name__)



def _prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df["_loaded_at"] = datetime.now()
    df["_source"] = "sharepoint"
    return df

def _ensure_schema_exists(engine, schema: str):
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))

def load_to_raw_full_replace(df: pd.DataFrame, schema: str, table_name: str):
    engine = get_engine()
    df = _prepare_dataframe(df)
    _ensure_schema_exists(engine, schema)

    with engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {schema}.{table_name} CASCADE"))

    total_rows = len(df)
    chunk_size = 1000
    for i in range(0, total_rows, chunk_size):
        mode = "replace" if i == 0 else "append"
        df.iloc[i:i + chunk_size].to_sql(name=table_name, con=engine, schema=schema, if_exists=mode, index=False)

    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {schema}.{table_name} ADD COLUMN id SERIAL PRIMARY KEY"))

    engine.dispose()
    logger.info("✓ %d rows loaded into %s.%s", total_rows, schema, table_name)
    return total_rows
