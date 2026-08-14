"""Fields extracted from Odoo for the stock loader (on-hand + lots + valuation)."""

STOCK_QUANT_FIELDS = [
    "id",
    "product_id",
    "location_id",
    "lot_id",
    "quantity",
    "reserved_quantity",
    "available_quantity",
    "warehouse_id",
    "product_uom_id",
    "in_date",
    "company_id",
    "package_id",
    "value",
    "x_myco_lot_spore_per_g",
    "x_myco_total_spores",
]

STOCK_LOT_FIELDS = [
    "id",
    "name",
    "ref",
    "product_id",
    "product_qty",
    "product_uom_id",
    "create_date",
    "company_id",
    "location_id",
    "x_myco_spore_per_g",
    "x_myco_total_spores",
    "x_lot_code_compact",
    "avg_cost",
    "total_value",
]

STOCK_VALUATION_LAYER_FIELDS = [
    "id",
    "product_id",
    "lot_id",
    "quantity",
    "unit_cost",
    "value",
    "remaining_qty",
    "remaining_value",
    "uom_id",
    "warehouse_id",
    "account_move_id",
    "description",
    "reference",
    "create_date",
    "company_id",
    "categ_id",
]

PRODUCT_FIELDS = [
    "id",
    "default_code",
    "display_name",
    "name",
    "categ_id",
    "uom_id",
    "barcode",
    "active",
    "type",
    "is_storable",
    "tracking",
    "standard_price",
]

STOCK_LOCATION_FIELDS = [
    "id",
    "name",
    "complete_name",
    "usage",
    "warehouse_id",
    "location_id",
    "company_id",
    "active",
]
