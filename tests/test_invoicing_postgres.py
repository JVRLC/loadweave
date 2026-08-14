import os
import unittest
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from loaders.business_data_loader.src.invoicing_views import recreate_invoicing_views


TEST_DATABASE_URL = os.getenv("INVOICING_TEST_DATABASE_URL")


@unittest.skipUnless(
    TEST_DATABASE_URL,
    "set INVOICING_TEST_DATABASE_URL to run PostgreSQL integration tests",
)
class InvoicingPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        url = make_url(TEST_DATABASE_URL)
        if url.database != "invoicing_test" or url.host not in {
            "localhost",
            "127.0.0.1",
        }:
            raise RuntimeError(
                "Integration tests only run against local database 'invoicing_test'"
            )

        cls.engine = create_engine(TEST_DATABASE_URL)
        with cls.engine.begin() as connection:
            connection.exec_driver_sql("DROP SCHEMA IF EXISTS fact CASCADE")
            connection.exec_driver_sql("DROP SCHEMA IF EXISTS dim CASCADE")
            connection.exec_driver_sql("DROP SCHEMA IF EXISTS raw CASCADE")
            connection.exec_driver_sql("CREATE SCHEMA raw")
            connection.execute(
                text(
                    """
                    CREATE TABLE raw.sales (
                        external_id text PRIMARY KEY,
                        name text,
                        opportunity_id text
                    );
                    CREATE TABLE raw.opportunities (
                        external_id text PRIMARY KEY,
                        country_id text,
                        x_myco_contract_type text,
                        x_myco_sector_id text
                    );
                    CREATE TABLE raw.invoices (
                        external_id text PRIMARY KEY,
                        name text,
                        partner_id text,
                        ref text,
                        invoice_origin text,
                        invoice_date timestamp,
                        invoice_date_due timestamp,
                        state text,
                        move_type text,
                        currency_id text,
                        company_currency_id text,
                        amount_untaxed numeric,
                        amount_total numeric,
                        amount_untaxed_signed numeric,
                        amount_total_signed numeric
                    );
                    CREATE TABLE raw.invoice_lines (
                        external_id text PRIMARY KEY,
                        move_id text,
                        product_id text,
                        quantity numeric,
                        price_unit numeric,
                        discount numeric,
                        price_subtotal numeric,
                        price_total numeric
                    );
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO raw.opportunities VALUES
                        ('opp-1', 'United States', 'PULSE - UPSELL', 'ppam');

                    INSERT INTO raw.sales VALUES
                        ('sale-1', 'DEV-001', 'opp-1'),
                        ('sale-2', 'DEV-002', NULL);

                    INSERT INTO raw.invoices VALUES
                        ('inv-1', 'FAC-001', 'Client A', NULL, 'DEV-001',
                         '2026-01-15', '2026-02-15', 'posted', 'out_invoice',
                         'EUR', 'EUR', 100, 120, 100, 120),
                        ('refund-1', 'AVOIR-001', 'Client A', NULL, 'DEV-001',
                         '2026-02-01', '2026-03-01', 'posted', 'out_refund',
                         'EUR', 'EUR', 10, 12, -10, -12),
                        ('manual-1', 'FAC-002', 'Client B', NULL, NULL,
                         '2026-04-10', '2026-05-10', 'posted', 'out_invoice',
                         'EUR', 'EUR', 50, 60, 50, 60),
                        ('unlinked-1', 'FAC-003', 'Client C', NULL, 'DEV-002',
                         '2026-04-11', '2026-05-11', 'posted', 'out_invoice',
                         'EUR', 'EUR', 20, 24, 20, 24),
                        ('draft-1', NULL, 'Client C', NULL, 'DEV-002',
                         '2026-04-12', '2026-05-12', 'draft', 'out_invoice',
                         'EUR', 'EUR', 500, 600, 500, 600),
                        ('cancel-1', 'AVOIR-002', 'Client A', NULL, 'DEV-001',
                         NULL, NULL, 'cancel', 'out_refund',
                         'EUR', 'EUR', 20, 24, -20, -24);

                    INSERT INTO raw.invoice_lines VALUES
                        ('line-1', 'inv-1', 'PULSE', 1, 100, 0, 100, 120),
                        ('line-2', 'refund-1', 'PULSE', 1, 10, 0, 10, 12),
                        ('line-3', 'manual-1', 'AUDIT', 1, 50, 0, 50, 60),
                        ('line-4', 'unlinked-1', 'READY', 1, 20, 0, 20, 24),
                        ('line-5', 'draft-1', 'READY', 1, 500, 0, 500, 600),
                        ('line-6', 'cancel-1', 'PULSE', 1, 20, 0, 20, 24);
                    """
                )
            )

        recreate_invoicing_views(cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def test_only_posted_documents_are_included_and_refund_is_negative(self):
        with self.engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT COUNT(*) AS documents,
                           SUM(amount_untaxed) AS amount_untaxed,
                           SUM(amount_total) AS amount_total
                    FROM fact.invoices
                    """
                )
            ).mappings().one()

        self.assertEqual(result["documents"], 4)
        self.assertEqual(result["amount_untaxed"], Decimal("160"))
        self.assertEqual(result["amount_total"], Decimal("192"))

    def test_product_lines_reconcile_with_invoice_headers(self):
        with self.engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT SUM(amount_untaxed) AS amount_untaxed,
                           SUM(amount_total) AS amount_total
                    FROM fact.invoice_lines
                    """
                )
            ).mappings().one()

        self.assertEqual(result["amount_untaxed"], Decimal("160"))
        self.assertEqual(result["amount_total"], Decimal("192"))

    def test_crm_dimensions_are_normalized_without_losing_manual_invoice(self):
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT invoice_id, country, contract_type, sector, crm_link_status
                    FROM fact.invoices
                    ORDER BY invoice_id
                    """
                )
            ).mappings().all()

        by_invoice = {row["invoice_id"]: row for row in rows}
        self.assertEqual(by_invoice["inv-1"]["country"], "États-Unis")
        self.assertEqual(by_invoice["inv-1"]["contract_type"], "pulse_upsell")
        self.assertEqual(by_invoice["inv-1"]["sector"], "PPAM")
        self.assertEqual(by_invoice["inv-1"]["crm_link_status"], "linked")
        self.assertEqual(by_invoice["manual-1"]["country"], "Non renseigné")
        self.assertEqual(
            by_invoice["manual-1"]["crm_link_status"], "missing_origin"
        )
        self.assertEqual(by_invoice["unlinked-1"]["country"], "Non renseigné")
        self.assertEqual(
            by_invoice["unlinked-1"]["crm_link_status"], "missing_opportunity"
        )


if __name__ == "__main__":
    unittest.main()
