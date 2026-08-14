from loaders.stock_data_loader.src.fields_config import (
    PRODUCT_FIELDS,
    STOCK_LOCATION_FIELDS,
    STOCK_LOT_FIELDS,
    STOCK_QUANT_FIELDS,
    STOCK_VALUATION_LAYER_FIELDS,
)

STOCK_MODELS_CONFIG = [
    {
        "label": "products",
        "odoo_model": "product.product",
        "table_name": "products",
        "fields": PRODUCT_FIELDS,
        "domain": [],
        "strategy": "full_replace",
        "with_history": False,
    },
    {
        "label": "stock locations",
        "odoo_model": "stock.location",
        "table_name": "stock_locations",
        "fields": STOCK_LOCATION_FIELDS,
        "domain": [],
        "strategy": "full_replace",
        "with_history": False,
    },
    {
        "label": "stock lots",
        "odoo_model": "stock.lot",
        "table_name": "stock_lots",
        "fields": STOCK_LOT_FIELDS,
        "domain": [],
        "strategy": "full_replace",
        "with_history": False,
    },
    {
        "label": "stock quants",
        "odoo_model": "stock.quant",
        "table_name": "stock_quants",
        "fields": STOCK_QUANT_FIELDS,
        # On-hand stock only (skip virtual / supplier / customer / inventory loss).
        "domain": [["location_id.usage", "=", "internal"]],
        "strategy": "full_replace",
        "with_history": False,
    },
    {
        "label": "stock valuation layers",
        "odoo_model": "stock.valuation.layer",
        "table_name": "stock_valuation_layers",
        "fields": STOCK_VALUATION_LAYER_FIELDS,
        "domain": [],
        "strategy": "full_replace",
        "with_history": False,
    },
]
