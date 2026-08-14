"""
Configuration of fields to extract from Odoo for each table.
This file centralizes field definitions to facilitate maintenance
and allow modifications without touching the main code.
"""

OPPORTUNITY_FIELDS = [
    "id",
    "name",
    "partner_id",
    "user_id",
    "stage_id",
    "priority",
    "partner_name",
    "contact_name",
    "source_id",
    "lost_reason_id",
    "expected_revenue",
    "probability",
    "date_deadline",
    "date_closed",
    "date_open",
    "date_last_stage_update",
    "active",
    "won_status",
    "create_date",
    "city",
    "prorated_revenue",
    # Custom fields
    "x_myco_bio_status",
    "x_myco_suspension_reason",
    "x_myco_contract_type",
    "x_myco_crop_type",
    "x_myco_opportunity_hectares",
    "x_myco_sales_confidence",
    # "x_myco_date_won",
    "x_myco_sellsy_id",
    "x_myco_target_mix",
    "x_myco_activity_ids",
    "x_myco_sector_id",
    "x_myco_product_delivery_date",
    "x_myco_inoculation_date",
    "x_myco_agri_pm_id",
    "x_myco_inoculation_city",
    "x_myco_inoculation_country_id",
    "x_myco_issue_ids",
    "country_id",
]

# Simplified CONTACT_FIELDS - only basic and custom fields to avoid permission issues
CONTACT_FIELDS = [
    "id",
    "firstname",
    "category_id",
    "lastname",
    "user_id",
    "function",
    "create_date",
    "is_company",
    # Custom fields
    "x_myco_recipient_pole",
    "x_myco_contact_source",
    "x_myco_contact_subsource",
    "x_myco_urgency_level",
    "x_myco_high_potential",
    "x_myco_qualification_result",
    "x_myco_status",
    "x_myco_brought_by",
    # x_myco_secondary_function removed — field no longer exists on res.partner in Odoo
    "x_myco_decision_power",
    "x_myco_total_hectares",
    "x_myco_contact_source_category",
]

# Fields fetched from sale.order (header) — used to enrich each line
SALE_ORDER_FIELDS = [
    "id",
    "user_id", # sales person
    "name",  # quote name/number
    "sale_order_template_id",  # type of contract (e.g., "START")
    "partner_invoice_id",  # facturation address
    "partner_shipping_id",  # facturation delivery address
    "date_order",  # creation date of the order
    "validity_date",  # expiration date of the quote
    "payment_term_id",  # payment terms
    "pricelist_id",  # pricelist
    "state",  # status (e.g., 'draft', 'sent', 'sale', etc.)
    "incoterm",  # INCOTERM
    "opportunity_id",  # linked opportunity
    "amount_untaxed",  # amount HT total
    "amount_tax",  # total tax amount
    "amount_total",  # amount TTC total
    "create_date",
    "signed_by",  # name typed by client on the portal signature widget
    "signed_on",  # datetime of client e-signature (non-null = signed)
]

# Fields fetched from sale.order.line — joined with header fields above
SALE_LINE_FIELDS = [
    "id",
    "order_id",  # link to sale.order (kept as ID via SPECIAL_FIELD_HANDLING)
    "order_partner_id",  # client (related field: order_id.partner_id)
    "product_id",  # intern ref + product name ([id, "[ref] nom"])
    "product_uom_qty",  # Qty
    "price_unit",
    "discount",
    "price_subtotal",  # amount HT
    "price_total",  # amount TTC
    "tax_id",  # Tax
    "product_uom",  # unit of measure (e.g., 'kg', 'unit', etc.)
]

# Simplified CLIENT_FIELDS - only basic and custom fields to avoid permission issues
CLIENT_FIELDS = [
    "id",
    "name",
    "ref",
    "industry_id",
    "company_registry",
    "email",
    "phone",
    "mobile",
    "function",
    "comment",
    "city",
    "vat",
    "website",
    "siret",
    "create_date",
    "lang",
    # Custom fields
    "x_myco_status",
    "x_myco_rcs",
    "x_myco_naf_code",
    "x_myco_sellsy_id",
    "x_myco_qualification_result",
    "x_myco_urgency_level",
    "x_myco_high_potential",
    "x_myco_issue_ids",
    "x_myco_total_hectares",
    "x_myco_potential_amount",
]


COMPTABILITY_FIELDS = [
    "id",
    "name",
    "partner_id",
    "ref",
    "invoice_date",  # invoice date
    "invoice_date_due",  # due date
    "state",
    "move_type",  # out_invoice or out_refund
    "delivery_date",  # delivery date
    "partner_shipping_id",  # delivery address (used to get delivery city)
    "currency_id",
    "company_currency_id",  # reporting currency used by the signed amounts
    "amount_untaxed",
    "amount_tax",
    "amount_total",
    "amount_untaxed_signed",  # company currency; refunds are negative
    "amount_total_signed",  # company currency; refunds are negative
    "invoice_origin",  # source quote number; links to raw.sales.name
]


INVOICE_LINE_FIELDS = [
    "id",
    "move_id",          # lien vers account.move (kept as ID)
    "partner_id",       # client
    "product_id",       
    "quantity",         
    "price_unit",      
    "discount",        
    "price_subtotal",   # HT
    "price_total",      # TTC
    "tax_ids",          
    "product_uom_id",   # unit of mesure
]
