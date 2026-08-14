-- partner_shipping_id in raw.invoices actually holds the partner NAME
-- (resolved by enrich_with_delivery_city), not the Odoo ID. Rename for clarity.
ALTER TABLE raw.invoices
    RENAME COLUMN partner_shipping_id TO partner_shipping_name;
