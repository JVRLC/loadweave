import logging
from decimal import Decimal

from sqlalchemy import text


logger = logging.getLogger(__name__)


# A quote number should identify one sale order. Aggregating first protects the
# invoice grain if bad source data ever contains duplicate sale.order names.
_SALES_MATCH_CTE = """
sales_by_origin AS (
    SELECT
        name,
        COUNT(*) AS match_count,
        CASE WHEN COUNT(*) = 1 THEN MIN(opportunity_id) END AS opportunity_id
    FROM raw.sales
    WHERE name IS NOT NULL
    GROUP BY name
)
"""


# Power BI views for the invoicing dashboard. The fact views intentionally:
# - keep posted customer invoices and refunds only;
# - use Odoo's signed company-currency amounts (refunds are negative);
# - retain invoices without a CRM link under "Non renseigné";
# - expose the CRM link status so missing source data is measurable.
_VIEWS = {
    "dim.offer": """
        CREATE OR REPLACE VIEW dim.offer AS
        SELECT
            ROW_NUMBER() OVER (ORDER BY name) AS id,
            name
        FROM (
            SELECT DISTINCT COALESCE(lines.product_id, 'Non renseigné') AS name
            FROM raw.invoice_lines AS lines
            JOIN raw.invoices AS invoices
              ON invoices.external_id = lines.move_id
            WHERE invoices.state = 'posted'
              AND invoices.move_type IN ('out_invoice', 'out_refund')
        ) AS offers
    """,
    "dim.invoice_link": f"""
        CREATE OR REPLACE VIEW dim.invoice_link AS
        WITH {_SALES_MATCH_CTE}
        SELECT
            invoices.external_id AS invoice_external_id,
            opportunities.country_id,
            opportunities.x_myco_contract_type AS contract_type,
            opportunities.x_myco_sector_id AS sector,
            CASE
                WHEN NULLIF(BTRIM(invoices.invoice_origin), '') IS NULL
                    THEN 'missing_origin'
                WHEN COALESCE(sales.match_count, 0) = 0
                    THEN 'sale_not_found'
                WHEN sales.match_count > 1
                    THEN 'ambiguous_origin'
                WHEN sales.opportunity_id IS NULL
                    THEN 'missing_opportunity'
                WHEN opportunities.external_id IS NULL
                    THEN 'opportunity_not_found'
                ELSE 'linked'
            END AS link_status
        FROM raw.invoices AS invoices
        LEFT JOIN sales_by_origin AS sales
          ON sales.name = invoices.invoice_origin
        LEFT JOIN raw.opportunities AS opportunities
          ON opportunities.external_id = sales.opportunity_id
    """,
    "fact.invoices": f"""
        CREATE OR REPLACE VIEW fact.invoices AS
        WITH {_SALES_MATCH_CTE}
        SELECT
            invoices.external_id AS invoice_id,
            invoices.name AS invoice_number,
            invoices.partner_id AS customer,
            invoices.ref AS customer_reference,
            invoices.invoice_origin,
            invoices.invoice_date::date AS invoice_date,
            invoices.invoice_date_due::date AS due_date,
            DATE_TRUNC('quarter', invoices.invoice_date)::date AS quarter_start,
            EXTRACT(YEAR FROM invoices.invoice_date)::int AS invoice_year,
            EXTRACT(QUARTER FROM invoices.invoice_date)::int AS quarter_number,
            'T' || EXTRACT(QUARTER FROM invoices.invoice_date)::int
                || ' ' || EXTRACT(YEAR FROM invoices.invoice_date)::int
                AS quarter_label,
            invoices.move_type,
            CASE invoices.move_type
                WHEN 'out_invoice' THEN 'Facture'
                WHEN 'out_refund' THEN 'Avoir'
            END AS document_type,
            invoices.currency_id AS document_currency,
            invoices.company_currency_id AS reporting_currency,
            COALESCE(
                invoices.amount_untaxed_signed,
                CASE invoices.move_type
                    WHEN 'out_refund' THEN -COALESCE(invoices.amount_untaxed, 0)
                    ELSE COALESCE(invoices.amount_untaxed, 0)
                END
            ) AS amount_untaxed,
            COALESCE(
                invoices.amount_total_signed,
                CASE invoices.move_type
                    WHEN 'out_refund' THEN -COALESCE(invoices.amount_total, 0)
                    ELSE COALESCE(invoices.amount_total, 0)
                END
            ) - COALESCE(
                invoices.amount_untaxed_signed,
                CASE invoices.move_type
                    WHEN 'out_refund' THEN -COALESCE(invoices.amount_untaxed, 0)
                    ELSE COALESCE(invoices.amount_untaxed, 0)
                END
            ) AS amount_tax,
            COALESCE(
                invoices.amount_total_signed,
                CASE invoices.move_type
                    WHEN 'out_refund' THEN -COALESCE(invoices.amount_total, 0)
                    ELSE COALESCE(invoices.amount_total, 0)
                END
            ) AS amount_total,
            COALESCE(
                CASE opportunities.country_id
                    WHEN 'Belgium' THEN 'Belgique'
                    WHEN 'Morocco' THEN 'Maroc'
                    WHEN 'Netherlands' THEN 'Pays-Bas'
                    WHEN 'Poland' THEN 'Pologne'
                    WHEN 'Romania' THEN 'Roumanie'
                    WHEN 'Spain' THEN 'Espagne'
                    WHEN 'Switzerland' THEN 'Suisse'
                    WHEN 'Ireland' THEN 'Irlande'
                    WHEN 'Senegal' THEN 'Sénégal'
                    WHEN 'United States' THEN 'États-Unis'
                    ELSE NULLIF(BTRIM(opportunities.country_id), '')
                END,
                'Non renseigné'
            ) AS country,
            COALESCE(
                CASE LOWER(NULLIF(BTRIM(opportunities.x_myco_contract_type), ''))
                    WHEN 'pulse - upsell' THEN 'pulse_upsell'
                    ELSE LOWER(NULLIF(BTRIM(opportunities.x_myco_contract_type), ''))
                END,
                'Non renseigné'
            ) AS contract_type,
            COALESCE(
                CASE
                    WHEN UPPER(NULLIF(BTRIM(opportunities.x_myco_sector_id), '')) = 'PPAM'
                        THEN 'PPAM'
                    ELSE NULLIF(BTRIM(opportunities.x_myco_sector_id), '')
                END,
                'Non renseigné'
            ) AS sector,
            CASE
                WHEN NULLIF(BTRIM(invoices.invoice_origin), '') IS NULL
                    THEN 'missing_origin'
                WHEN COALESCE(sales.match_count, 0) = 0
                    THEN 'sale_not_found'
                WHEN sales.match_count > 1
                    THEN 'ambiguous_origin'
                WHEN sales.opportunity_id IS NULL
                    THEN 'missing_opportunity'
                WHEN opportunities.external_id IS NULL
                    THEN 'opportunity_not_found'
                ELSE 'linked'
            END AS crm_link_status
        FROM raw.invoices AS invoices
        LEFT JOIN sales_by_origin AS sales
          ON sales.name = invoices.invoice_origin
        LEFT JOIN raw.opportunities AS opportunities
          ON opportunities.external_id = sales.opportunity_id
        WHERE invoices.state = 'posted'
          AND invoices.move_type IN ('out_invoice', 'out_refund')
    """,
    "fact.invoice_lines": """
        CREATE OR REPLACE VIEW fact.invoice_lines AS
        SELECT
            lines.external_id AS invoice_line_id,
            facts.invoice_id,
            facts.invoice_number,
            facts.customer,
            facts.invoice_origin,
            facts.invoice_date,
            facts.due_date,
            facts.quarter_start,
            facts.invoice_year,
            facts.quarter_number,
            facts.quarter_label,
            facts.move_type,
            facts.document_type,
            facts.document_currency,
            facts.reporting_currency,
            facts.country,
            facts.contract_type,
            facts.sector,
            facts.crm_link_status,
            COALESCE(lines.product_id, 'Non renseigné') AS offer,
            CASE facts.move_type
                WHEN 'out_refund' THEN -COALESCE(lines.quantity, 0)
                ELSE COALESCE(lines.quantity, 0)
            END AS quantity,
            lines.price_unit AS unit_price_document_currency,
            lines.discount,
            CASE
                WHEN COALESCE(invoices.amount_untaxed, 0) = 0 THEN 0
                ELSE COALESCE(lines.price_subtotal, 0)
                    * facts.amount_untaxed / invoices.amount_untaxed
            END AS amount_untaxed,
            CASE
                WHEN COALESCE(invoices.amount_total, 0) = 0 THEN 0
                ELSE COALESCE(lines.price_total, 0)
                    * facts.amount_total / invoices.amount_total
            END - CASE
                WHEN COALESCE(invoices.amount_untaxed, 0) = 0 THEN 0
                ELSE COALESCE(lines.price_subtotal, 0)
                    * facts.amount_untaxed / invoices.amount_untaxed
            END AS amount_tax,
            CASE
                WHEN COALESCE(invoices.amount_total, 0) = 0 THEN 0
                ELSE COALESCE(lines.price_total, 0)
                    * facts.amount_total / invoices.amount_total
            END AS amount_total
        FROM raw.invoice_lines AS lines
        JOIN raw.invoices AS invoices
          ON invoices.external_id = lines.move_id
        JOIN fact.invoices AS facts
          ON facts.invoice_id = invoices.external_id
    """,
}


_VALIDATION_QUERY = """
    SELECT
        (SELECT COUNT(*) FROM fact.invoices) AS invoice_count,
        (SELECT COUNT(DISTINCT invoice_id) FROM fact.invoice_lines) AS line_invoice_count,
        (SELECT COALESCE(SUM(amount_untaxed), 0) FROM fact.invoices)
            AS invoice_amount_untaxed,
        (SELECT COALESCE(SUM(amount_untaxed), 0) FROM fact.invoice_lines)
            AS line_amount_untaxed,
        (SELECT COALESCE(SUM(amount_total), 0) FROM fact.invoices)
            AS invoice_amount_total,
        (SELECT COALESCE(SUM(amount_total), 0) FROM fact.invoice_lines)
            AS line_amount_total
"""


def recreate_invoicing_views(engine):
    """Create the invoicing reporting model and log its reconciliation."""
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS dim")
        conn.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS fact")
        # DROP first: CREATE OR REPLACE cannot change/drop columns on an existing view.
        # Reverse order so dependents (fact.invoice_lines → fact.invoices) go first.
        for view_name in reversed(list(_VIEWS)):
            conn.execute(text(f"DROP VIEW IF EXISTS {view_name} CASCADE"))
        for view_name, sql in _VIEWS.items():
            conn.execute(text(sql))
            logger.info("Recreated view %s", view_name)

        metrics = conn.execute(text(_VALIDATION_QUERY)).mappings().one()
        untaxed_difference = (
            metrics["invoice_amount_untaxed"] - metrics["line_amount_untaxed"]
        )
        total_difference = (
            metrics["invoice_amount_total"] - metrics["line_amount_total"]
        )
        logger.info(
            "Invoicing views: %s posted documents, %s represented by product lines; "
            "HT difference=%s, TTC difference=%s",
            metrics["invoice_count"],
            metrics["line_invoice_count"],
            untaxed_difference,
            total_difference,
        )
        if (
            metrics["invoice_count"] != metrics["line_invoice_count"]
            or abs(untaxed_difference) > Decimal("0.01")
            or abs(total_difference) > Decimal("0.01")
        ):
            logger.warning(
                "Invoice headers and product lines do not fully reconcile; "
                "check posted invoices without product lines or rounding differences"
            )
