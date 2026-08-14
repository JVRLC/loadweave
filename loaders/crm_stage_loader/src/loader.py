from datetime import date, timedelta
from sqlalchemy import text
from loaders.db import get_engine
from loaders.odoo_extract import _authenticate, ODOO_DB, ODOO_ADMIN_PASSWORD


TODAY = date.today()
S_1 = TODAY - timedelta(days=7)


def _fetch_stage_changes(since: str) -> list[dict]:
    """Fetch CRM stage changes from Odoo via XMLRPC since a given date."""
    db, password = ODOO_DB, ODOO_ADMIN_PASSWORD
    uid, models = _authenticate()

    tracking = models.execute_kw(
        db, uid, password, "mail.tracking.value", "search_read",
        [[
            ["field_id.name", "=", "stage_id"],
            ["mail_message_id.model", "=", "crm.lead"],
            ["mail_message_id.date", ">=", since],
        ]],
        {"fields": ["old_value_char", "new_value_char", "mail_message_id"]},
    )

    if not tracking:
        return []

    message_ids = [t["mail_message_id"][0] for t in tracking]
    messages = models.execute_kw(
        db, uid, password, "mail.message", "search_read",
        [[["id", "in", message_ids]]],
        {"fields": ["id", "res_id", "date"]},
    )
    message_map = {m["id"]: m for m in messages}

    lead_ids = list({m["res_id"] for m in messages})
    leads = models.execute_kw(
        db, uid, password, "crm.lead", "search_read",
        [[["id", "in", lead_ids]]],
        {"fields": ["id", "name", "partner_name", "user_id", "expected_revenue"]},
    )
    lead_map = {l["id"]: l for l in leads}

    rows = []
    for t in tracking:
        msg = message_map.get(t["mail_message_id"][0])
        if not msg:
            continue
        lead = lead_map.get(msg["res_id"])
        if not lead:
            continue

        rows.append({
            "opp_id":          lead["id"],
            "opportunite":     lead["name"],
            "client":          lead["partner_name"] or None,
            "commercial":      lead["user_id"][0] if lead["user_id"] else None,
            "etape_avant":     t["old_value_char"] or None,
            "etape_apres":     t["new_value_char"] or None,
            "date_changement": msg["date"],
            "montant":         lead["expected_revenue"] or None,
        })

    return rows


def load_stage_changes(since: str = S_1.isoformat()) -> None:
    rows = _fetch_stage_changes(since)
    print(f"{len(rows)} changes detected since {since}")

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE raw.stage_changes"))
        if rows:
            conn.execute(
                text("""
                    INSERT INTO raw.stage_changes
                        (opp_id, opportunite, client, commercial,
                         etape_avant, etape_apres, date_changement, montant)
                    VALUES
                        (:opp_id, :opportunite, :client, :commercial,
                         :etape_avant, :etape_apres, :date_changement, :montant)
                    ON CONFLICT (opp_id, date_changement, etape_avant, etape_apres) DO NOTHING
                """),
                rows,
            )
    engine.dispose()
    print(f"{len(rows)} rows inserted into raw.stage_changes")
