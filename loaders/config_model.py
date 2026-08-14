from loaders.fields_config import (
    OPPORTUNITY_FIELDS,
    CONTACT_FIELDS,
    CLIENT_FIELDS,
    SALE_ORDER_FIELDS,
    SALE_LINE_FIELDS,
    COMPTABILITY_FIELDS,
    INVOICE_LINE_FIELDS,
)
from loaders.odoo_extract import enrich_with_delivery_city

MODELS_CONFIG = [
    {
        "label": "opportunities",
        "odoo_model": "crm.lead",
        "table_name": "opportunities",
        "fields": OPPORTUNITY_FIELDS,
        "domain": [],
        "strategy": "full_replace",
        "with_history": False,
    },
    {
        "label": "contacts",
        "odoo_model": "res.partner",
        "table_name": "contacts",
        "fields": CONTACT_FIELDS,
        "domain": [["customer_rank", "=", 0]],
        "strategy": "full_replace",  
        "with_history": False,
    },
    {
        "label": "clients",
        "odoo_model": "res.partner",
        "table_name": "clients",
        "fields": CLIENT_FIELDS,
        "domain": [["customer_rank", ">", 0]],
        "strategy": "incremental",  # only update existing clients, do not delete
        "with_history": False,
    },
    {
        "label": "sales",
        "odoo_model": "sale.order",
        "table_name": "sales",
        "fields": SALE_ORDER_FIELDS,
        "domain": [],
        "strategy": "full_replace",
        "with_history": False,
    },
    {
        "label": "sale_lines",
        "odoo_model": "sale.order.line",
        "table_name": "sale_lines",
        "fields": SALE_LINE_FIELDS,
        "domain": [["is_downpayment", "=", False]],
        "strategy": "full_replace",
        "with_history": False,
    },
    {
        "label": "invoices",
        "odoo_model": "account.move",
        "table_name": "invoices",
        "fields": COMPTABILITY_FIELDS,
        # partner_shipping_id is fetched from Odoo but not stored as-is;
        # enrich_with_delivery_city resolves it into partner_shipping_name + delivery_city.
        "db_columns": [c for c in COMPTABILITY_FIELDS if c != "partner_shipping_id"]
        + ["partner_shipping_name", "delivery_city"],
        "domain": [["move_type", "in", ["out_invoice", "out_refund"]]],
        "strategy": "full_replace",
        "with_history": False,
        "post_process": enrich_with_delivery_city,
    },
    {
        "label": "invoice_lines",
        "odoo_model": "account.move.line",
        "table_name": "invoice_lines",
        "fields": INVOICE_LINE_FIELDS,
        "domain": [
            ["move_type", "in", ["out_invoice", "out_refund"]],
            ["display_type", "=", "product"],
        ],
        "strategy": "full_replace",
        "with_history": False,
    },
]
