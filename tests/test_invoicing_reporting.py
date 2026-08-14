import unittest
from decimal import Decimal

from sqlalchemy import Numeric
from sqlalchemy.sql.elements import TextClause

from loaders.business_data_loader.src.invoicing_views import (
    _VALIDATION_QUERY,
    _VIEWS,
    recreate_invoicing_views,
)
from loaders.config_model import MODELS_CONFIG
from loaders.fields_config import COMPTABILITY_FIELDS
from loaders.o2dw import COLUMN_TYPE_MAP


class _FakeMappingsResult:
    def __init__(self, metrics):
        self._metrics = metrics

    def mappings(self):
        return self

    def one(self):
        return self._metrics


class _FakeConnection:
    def __init__(self, metrics):
        self.metrics = metrics
        self.driver_sql = []
        self.statements = []

    def exec_driver_sql(self, statement):
        self.driver_sql.append(statement)

    def execute(self, statement):
        assert isinstance(statement, TextClause)
        sql = str(statement)
        self.statements.append(sql)
        if sql == _VALIDATION_QUERY:
            return _FakeMappingsResult(self.metrics)
        return _FakeMappingsResult({})


class _FakeBegin:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class _FakeEngine:
    def __init__(self, metrics):
        self.connection = _FakeConnection(metrics)

    def begin(self):
        return _FakeBegin(self.connection)


class InvoicingExtractionTests(unittest.TestCase):
    def test_invoice_extraction_contains_reporting_fields(self):
        required_fields = {
            "move_type",
            "company_currency_id",
            "amount_untaxed_signed",
            "amount_total_signed",
            "invoice_origin",
        }
        self.assertTrue(required_fields.issubset(COMPTABILITY_FIELDS))

    def test_signed_amounts_are_loaded_as_numeric(self):
        self.assertIs(COLUMN_TYPE_MAP["amount_untaxed_signed"], Numeric)
        self.assertIs(COLUMN_TYPE_MAP["amount_total_signed"], Numeric)

    def test_invoice_domain_keeps_invoices_and_refunds(self):
        invoice_config = next(
            config for config in MODELS_CONFIG if config["label"] == "invoices"
        )
        self.assertEqual(
            invoice_config["domain"],
            [["move_type", "in", ["out_invoice", "out_refund"]]],
        )


class InvoicingViewTests(unittest.TestCase):
    def test_fact_views_apply_accounting_rules(self):
        invoice_sql = _VIEWS["fact.invoices"]
        line_sql = _VIEWS["fact.invoice_lines"]

        self.assertIn("invoices.state = 'posted'", invoice_sql)
        self.assertIn("invoices.amount_total_signed", invoice_sql)
        self.assertIn("WHEN 'out_refund' THEN -COALESCE", invoice_sql)
        self.assertIn("LEFT JOIN raw.opportunities", invoice_sql)
        self.assertIn("'Non renseigné'", invoice_sql)
        self.assertIn("crm_link_status", invoice_sql)
        self.assertIn("facts.amount_total / invoices.amount_total", line_sql)

    def test_invoice_link_preserves_unmatched_invoices(self):
        link_sql = _VIEWS["dim.invoice_link"]

        self.assertIn("LEFT JOIN sales_by_origin", link_sql)
        self.assertIn("LEFT JOIN raw.opportunities", link_sql)
        self.assertIn("missing_origin", link_sql)
        self.assertIn("missing_opportunity", link_sql)

    def test_recreate_builds_schemas_views_and_reconciliation(self):
        metrics = {
            "invoice_count": 29,
            "line_invoice_count": 29,
            "invoice_amount_untaxed": Decimal("162991.52"),
            "line_amount_untaxed": Decimal("162991.52"),
            "invoice_amount_total": Decimal("183804.59"),
            "line_amount_total": Decimal("183804.59"),
        }
        engine = _FakeEngine(metrics)

        recreate_invoicing_views(engine)

        self.assertEqual(
            engine.connection.driver_sql,
            [
                "CREATE SCHEMA IF NOT EXISTS dim",
                "CREATE SCHEMA IF NOT EXISTS fact",
            ],
        )
        self.assertEqual(len(engine.connection.statements), len(_VIEWS) + 1)
        self.assertEqual(engine.connection.statements[-1], _VALIDATION_QUERY)

    def test_reconciliation_mismatch_is_reported(self):
        metrics = {
            "invoice_count": 2,
            "line_invoice_count": 1,
            "invoice_amount_untaxed": Decimal("100"),
            "line_amount_untaxed": Decimal("90"),
            "invoice_amount_total": Decimal("120"),
            "line_amount_total": Decimal("108"),
        }
        engine = _FakeEngine(metrics)

        with self.assertLogs(
            "loaders.business_data_loader.src.invoicing_views", level="WARNING"
        ) as logs:
            recreate_invoicing_views(engine)

        self.assertIn("do not fully reconcile", " ".join(logs.output))


if __name__ == "__main__":
    unittest.main()
