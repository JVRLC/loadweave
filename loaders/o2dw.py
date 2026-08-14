import logging
import os
import time
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table, Column, String, Numeric
from sqlalchemy import func, Integer, Date, TIMESTAMP, Index, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

logger = logging.getLogger(__name__)

# Database connection parameters
load_dotenv()
USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
HOST = os.getenv("DB_HOST")
PORT = os.getenv("DB_PORT")

COLUMN_TYPE_MAP = {
    # Opportunities
    "date_deadline": TIMESTAMP,
    "date_closed": TIMESTAMP,
    "date_open": TIMESTAMP,
    "date_last_stage_update": TIMESTAMP,
    "x_myco_date_won": TIMESTAMP,
    "x_myco_product_delivery_date": TIMESTAMP,
    "x_myco_inoculation_date": TIMESTAMP,
    "probability": Numeric,
    "expected_revenue": Numeric,
    "prorated_revenue": Numeric,
    "x_myco_opportunity_hectares": Numeric,
    # Contacts / Clients
    "x_myco_total_hectares": Numeric,
    "x_myco_potential_amount": Numeric,
    # Sales (sale.order)
    "date_order": TIMESTAMP,
    "validity_date": TIMESTAMP,
    "create_date": TIMESTAMP,
    "amount_untaxed": Numeric,
    "amount_tax": Numeric,
    "amount_total": Numeric,
    "amount_untaxed_signed": Numeric,
    "amount_total_signed": Numeric,
    "signed_on": TIMESTAMP,
    # Sale lines (sale.order.line)
    "product_uom_qty": Numeric,
    "price_unit": Numeric,
    "discount": Numeric,
    "price_subtotal": Numeric,
    "price_total": Numeric,
    # Invoices (account.move)
    "invoice_date": TIMESTAMP,
    "invoice_date_due": TIMESTAMP,
    "delivery_date": TIMESTAMP,
    # Invoice lines (account.move.line) / stock valuation
    "quantity": Numeric,
    "price_unit": Numeric,
    "discount": Numeric,
    "price_subtotal": Numeric,
    "price_total": Numeric,
    # Stock quants
    "reserved_quantity": Numeric,
    "available_quantity": Numeric,
    "value": Numeric,
    "x_myco_lot_spore_per_g": Numeric,
    "x_myco_total_spores": Numeric,
    "x_myco_spore_per_g": Numeric,
    "in_date": TIMESTAMP,
    # Stock lots
    "product_qty": Numeric,
    "avg_cost": Numeric,
    "total_value": Numeric,
    # Stock valuation layers
    "unit_cost": Numeric,
    "remaining_qty": Numeric,
    "remaining_value": Numeric,
    # Products
    "standard_price": Numeric,
}


def get_column_type(column_name: str):
    return COLUMN_TYPE_MAP.get(column_name, String)


def normalize_odoo_value(value):
    if value is False or value is None:
        return None
    return str(value)


def setup_database():
    max_retries = 5
    retry_delay = 3  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            engine = create_engine(
                f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}"
            )
            with engine.begin() as conn:
                conn.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS raw")

            logger.info("Database connection established (attempt %d/%d)", attempt, max_retries)
            return engine

        except Exception as e:
            if attempt < max_retries:
                logger.warning(
                    "Connection attempt %d/%d failed: %s", attempt, max_retries, str(e)[:80]
                )
                logger.info("Retrying in %ds...", retry_delay)
                time.sleep(retry_delay)
            else:
                raise RuntimeError(
                    f"Failed to connect to database after {max_retries} attempts. "
                    f"Check that PostgreSQL is running at {HOST}:{PORT}"
                ) from e


def get_existing_ids(engine, table_name):
    try:
        with engine.connect() as conn:
            query = text(f"SELECT external_id FROM raw.{table_name}")
            result = conn.execute(query)
            existing_ids = {row[0] for row in result}
            logger.info("Found %d existing records in %s", len(existing_ids), table_name)
            return existing_ids
    except Exception:
        logger.info("No existing data in %s (first run or table does not exist)", table_name)
        return set()


def create_odoo_table(engine, table_name, columns_list, with_history=False):
    if "id" not in columns_list:
        raise ValueError("columns_list must contain 'id' column")

    metadata = MetaData(schema="raw")
    extra_columns = [col for col in columns_list if col != "id"]

    if with_history:
        columns = [
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("external_id", String, nullable=False, index=True),
            Column(
                "snapshot_date", TIMESTAMP, server_default=func.now(), nullable=False
            ),
            Column(
                "snapshot_day", Date, server_default=func.current_date(), nullable=False
            ),
        ]
        columns.extend(
            [Column(col, get_column_type(col), nullable=True) for col in extra_columns]
        )

        table = Table(table_name, metadata, *columns)

        Index(
            f"idx_{table_name}_external_snapshot",
            table.c.external_id,
            table.c.snapshot_date.desc(),
        )
        Index(
            f"idx_{table_name}_external_snapshot_day",
            table.c.external_id,
            table.c.snapshot_day,
            unique=True,
        )
    else:
        columns = [
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("external_id", String, nullable=False, unique=True, index=True),
        ]
        columns.extend(
            [Column(col, get_column_type(col), nullable=True) for col in extra_columns]
        )

        table = Table(table_name, metadata, *columns)

    metadata.create_all(engine, checkfirst=True)

    # Add missing columns and fix wrong types for existing tables
    with engine.begin() as conn:
        for col in extra_columns:
            col_type = get_column_type(col)
            if col_type == Numeric:
                pg_type = "NUMERIC"
            elif col_type == TIMESTAMP:
                pg_type = "TIMESTAMP"
            else:
                pg_type = "TEXT"
            conn.execute(
                text(
                    f"ALTER TABLE raw.{table_name} "
                    f"ADD COLUMN IF NOT EXISTS {col} {pg_type}"
                )
            )
            # Migrate existing VARCHAR columns to correct type
            if col_type in (Numeric, TIMESTAMP):
                using_expr = f"{col}::NUMERIC" if col_type == Numeric else f"{col}::TIMESTAMP"
                result = conn.execute(text(
                    f"SELECT data_type FROM information_schema.columns "
                    f"WHERE table_schema = 'raw' AND table_name = :t AND column_name = :c"
                ), {"t": table_name, "c": col}).fetchone()
                if result and result[0] in ("character varying", "text"):
                    conn.execute(text(
                        f"ALTER TABLE raw.{table_name} "
                        f"ALTER COLUMN {col} TYPE {pg_type} USING {using_expr}"
                    ))

    if with_history:
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"ALTER TABLE raw.{table_name} "
                    f"ADD COLUMN IF NOT EXISTS snapshot_day DATE DEFAULT CURRENT_DATE NOT NULL"
                )
            )
            conn.execute(
                text(
                    f"UPDATE raw.{table_name} SET snapshot_day = snapshot_date::date "
                    f"WHERE snapshot_day != snapshot_date::date"
                )
            )
            conn.execute(
                text(
                    f"""
                DELETE FROM raw.{table_name} a
                USING raw.{table_name} b
                WHERE a.external_id = b.external_id
                  AND a.snapshot_day = b.snapshot_day
                  AND a.id < b.id
            """
                )
            )

        with engine.begin() as conn:
            conn.execute(
                text(
                    f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{table_name}_external_snapshot_day "
                    f"ON raw.{table_name} (external_id, snapshot_day)"
                )
            )

    return table


def insert_records(engine, table, records, strategy="upsert", columns_list=None, batch_size=1000):

    if not records:
        logger.info("No records to insert into %s", table.name)
        return

    data_columns = [
        col
        for col in (columns_list or table.columns.keys())
        if col not in ("id", "external_id", "snapshot_date", "snapshot_day")
    ]

    rows = [
        {
            "external_id": str(record["id"]),
            **{col: normalize_odoo_value(record.get(col)) for col in data_columns},
        }
        for record in records
        if record.get("id")
    ]

    if not rows:
        logger.info("No valid records to insert into %s", table.name)
        return

    with engine.begin() as conn:

        if strategy == "full_replace":
            conn.exec_driver_sql(f"TRUNCATE raw.{table.name} CASCADE")

        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            stmt = pg_insert(table).values(batch)

            if strategy == "upsert":
                stmt = stmt.on_conflict_do_update(
                    index_elements=["external_id"],
                    set_={
                        col: stmt.excluded[col] for col in batch[0] if col != "external_id"
                    },
                )
            elif strategy == "incremental":
                stmt = stmt.on_conflict_do_nothing()

            conn.execute(stmt)

    logger.info("[%s] %d records into %s", strategy, len(rows), table.name)
