from loaders.odoo_extract import extract_from_odoo
from loaders.o2dw import (
    setup_database,
    get_existing_ids,
    create_odoo_table,
    insert_records,
)
from loaders.config_model import MODELS_CONFIG
from loaders.business_data_loader.src.invoicing_views import recreate_invoicing_views
from sqlalchemy import text


def migrate_model(engine, cfg):
    label = cfg["label"]
    table_name = cfg["table_name"]
    fields = cfg["fields"]
    db_columns = cfg.get("db_columns", fields)
    strategy = cfg["strategy"]

    print(f"Extracting {label} from Odoo...")

    records = extract_from_odoo(
        cfg["odoo_model"],
        fields=fields,
        domain=cfg["domain"],
        resolve_relations=True,
    )

    if not records:
        print(f"No {label} found in Odoo")
        return

    print(f"{len(records)} {label} extracted")

    if "post_process" in cfg:
        records = cfg["post_process"](records)

    if strategy == "incremental":
        existing_ids = get_existing_ids(engine, table_name)
        if existing_ids:
            records = [r for r in records if str(r.get("id")) not in existing_ids]

        if not records:
            print(f"No new {label} to insert")
            return

        print(f"{len(records)} new {label} to insert")

    table = create_odoo_table(
        engine, table_name, db_columns, with_history=cfg["with_history"]
    )
    insert_records(engine, table, records, strategy=strategy, columns_list=db_columns)


def update_expected_revenue_from_quotes(engine):
    """From "Accord de principe" onward (Accord de principe, Gagné), overwrite
    raw.opportunities.expected_revenue with the sum of amount_total across the
    opportunity's non-cancelled quotes (raw.sales) — several quotes are summed."""
    with engine.begin() as conn:
        result = conn.execute(text("""
            WITH quote_totals AS (
                SELECT opportunity_id, SUM(amount_total) AS montant_devis
                FROM raw.sales
                WHERE state <> 'cancel'
                GROUP BY opportunity_id
            )
            UPDATE raw.opportunities o
            SET expected_revenue = q.montant_devis
            FROM quote_totals q
            WHERE q.opportunity_id = o.external_id
              AND o.stage_id IN ('Accord de principe', 'Gagné')
        """))
    print(f"expected_revenue updated from quotes for {result.rowcount} opportunities")


def add_fk_constraints(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'fk_sale_lines_order_id'
                ) THEN
                    ALTER TABLE raw.sale_lines
                    ADD CONSTRAINT fk_sale_lines_order_id
                    FOREIGN KEY (order_id) REFERENCES raw.sales(external_id)
                    ON DELETE CASCADE;
                END IF;
            END $$;
        """))
    print("FK constraints applied")


def mig_insert():
    engine = setup_database()

    for cfg in MODELS_CONFIG:
        migrate_model(engine, cfg)

    update_expected_revenue_from_quotes(engine)
    add_fk_constraints(engine)
    recreate_invoicing_views(engine)
    print("MIGRATION COMPLETE")


if __name__ == "__main__":
    mig_insert()
