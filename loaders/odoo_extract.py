import logging
import os
import xmlrpc.client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_ADMIN_USER = os.getenv("ODOO_ADMIN_USER")
ODOO_ADMIN_PASSWORD = os.getenv("ODOO_ADMIN_PASSWORD")
# Field-name keys apply globally. "model.field" keys override for one model only
# (so stock keep_id does not break business loaders that resolve product_id to name).
SPECIAL_FIELD_HANDLING = {
    "order_id": "keep_id",        # needed to join sale.order.line with sale.order
    "order_partner_id": "keep_id",  # client ID directly on sale.order.line
    "partner_shipping_id": "keep_id",  # keep ID to resolve delivery city separately
    "move_id": "keep_id",         # needed to join account.move.line with account.move
    "opportunity_id": "keep_id",  # needed to join sale.order with crm.lead (raw.opportunities.external_id)
    # Stock loader — keep Odoo IDs for joins across quants / lots / valuation / dims
    "stock.quant.product_id": "keep_id",
    "stock.quant.location_id": "keep_id",
    "stock.quant.lot_id": "keep_id",
    "stock.quant.warehouse_id": "keep_id",
    "stock.quant.product_uom_id": "keep_id",
    "stock.quant.package_id": "keep_id",
    "stock.lot.product_id": "keep_id",
    "stock.lot.location_id": "keep_id",
    "stock.lot.product_uom_id": "keep_id",
    "stock.valuation.layer.product_id": "keep_id",
    "stock.valuation.layer.lot_id": "keep_id",
    "stock.valuation.layer.warehouse_id": "keep_id",
    "stock.valuation.layer.uom_id": "keep_id",
    "stock.valuation.layer.categ_id": "keep_id",
    "stock.valuation.layer.account_move_id": "keep_id",
    "product.product.categ_id": "keep_id",
    "product.product.uom_id": "keep_id",
    "stock.location.warehouse_id": "keep_id",
    "stock.location.location_id": "keep_id",
}


def _do_authenticate(user, password):
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common", allow_none=True)
    uid = common.authenticate(ODOO_DB, user, password, {})
    if not uid:
        raise ValueError("Odoo authentication failed. Check credentials in .env.")
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object", allow_none=True)
    return uid, models


def _authenticate():
    if not all([ODOO_URL, ODOO_DB, ODOO_ADMIN_USER, ODOO_ADMIN_PASSWORD]):
        raise ValueError(
            "Missing Odoo admin env vars: ODOO_URL, ODOO_DB, ODOO_ADMIN_USER, ODOO_ADMIN_PASSWORD."
        )
    return _do_authenticate(ODOO_ADMIN_USER, ODOO_ADMIN_PASSWORD)


def _batch_search_read(models, uid, model_name, fields, domain, batch_size=200):
    all_records = []
    offset = 0
    kwargs = {"limit": batch_size, "offset": offset}
    if fields:
        kwargs["fields"] = fields
    while True:
        kwargs["offset"] = offset
        batch = models.execute_kw(
            ODOO_DB, uid, ODOO_ADMIN_PASSWORD, model_name, "search_read", [domain or []], kwargs
        )
        if not batch:
            break
        all_records.extend(batch)
        offset += batch_size
    return all_records


def extract_from_odoo(
    model_name, fields=None, limit=None, domain=None, resolve_relations=False
):
    if not model_name:
        raise ValueError("You must provide a model_name to extract data from.")

    uid, models = _authenticate()

    if limit is not None:
        kwargs = {"limit": limit}
        if fields:
            kwargs["fields"] = fields
        records = models.execute_kw(
            ODOO_DB, uid, ODOO_ADMIN_PASSWORD, model_name, "search_read", [domain or []], kwargs
        )
    else:
        records = _batch_search_read(models, uid, model_name, fields, domain)

    if resolve_relations:
        records = resolve_relational_fields(model_name, records, uid, models)

    return records


def resolve_relational_fields(model_name, records, uid, models):
    if not records:
        return records

    try:
        fields_info = models.execute_kw(
            ODOO_DB,
            uid,
            ODOO_ADMIN_PASSWORD,
            model_name,
            "fields_get",
            [],
            {"attributes": ["type", "relation"]},
        )

        relational_fields = {
            name: meta
            for name, meta in fields_info.items()
            if meta.get("type") in ("many2one", "many2many", "one2many")
        }

        for record in records:
            for field_name, field_meta in relational_fields.items():
                if field_name not in record:
                    continue
                value = record[field_name]
                field_type = field_meta.get("type")

                if value is False or value is None:
                    record[field_name] = None
                elif field_type == "many2one":
                    if isinstance(value, list) and len(value) >= 2:
                        handling = SPECIAL_FIELD_HANDLING.get(
                            f"{model_name}.{field_name}"
                        ) or SPECIAL_FIELD_HANDLING.get(field_name)
                        if handling == "keep_id":
                            record[field_name] = str(value[0])
                        else:
                            record[field_name] = value[1]
                    elif isinstance(value, (int, str)):
                        record[field_name] = str(value)
                elif field_type in ("many2many", "one2many"):
                    if isinstance(value, list):
                        record[field_name] = ",".join(str(v) for v in value) or None
                    else:
                        record[field_name] = str(value) if value else None

        return records

    except Exception as e:
        logger.warning(
            "Could not resolve relational fields for %s: %s", model_name, str(e)[:100]
        )
        return records


def enrich_with_delivery_city(records):
    """Fetch city and name from res.partner for each partner_shipping_id.

    Adds delivery_city and partner_shipping_name; leaves partner_shipping_id
    (the raw Odoo ID) untouched.
    """
    partner_ids = []
    for r in records:
        pid = r.get("partner_shipping_id")
        if pid:
            try:
                partner_ids.append(int(pid))
            except (ValueError, TypeError):
                pass

    if not partner_ids:
        for r in records:
            r["delivery_city"] = None
            r["partner_shipping_name"] = None
        return records

    uid, models = _authenticate()
    unique_ids = list(set(partner_ids))
    partners = models.execute_kw(
        ODOO_DB, uid, ODOO_ADMIN_PASSWORD, "res.partner", "search_read",
        [[["id", "in", unique_ids]]],
        {"fields": ["id", "name", "city"]},
    )
    city_map = {p["id"]: p.get("city") or None for p in partners}
    name_map = {p["id"]: p.get("name") or None for p in partners}

    for record in records:
        pid = record.get("partner_shipping_id")
        try:
            int_pid = int(pid) if pid else None
            record["delivery_city"] = city_map.get(int_pid) if int_pid else None
            record["partner_shipping_name"] = name_map.get(int_pid) if int_pid else None
        except (ValueError, TypeError):
            record["delivery_city"] = None
            record["partner_shipping_name"] = None

    return records
