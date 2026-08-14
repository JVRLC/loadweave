# CRM Stage Loader

Loads CRM opportunity stage changes from Odoo into `raw.stage_changes` in the Data Warehouse.

## What it does

- Connects to Odoo via XML-RPC (admin account)
- Fetches all `stage_id` changes on `crm.lead` since a given date, via `mail.tracking.value`
- For each change: captures the stage before, the stage after, the date, and the opportunity amount at that point in time
- Truncates and reloads `raw.stage_changes` on every run

## Prerequisites

Variables in `.env.prod`:

| Variable | Description |
|---|---|
| `ODOO_URL` | Odoo instance URL |
| `ODOO_DB` | Odoo database name |
| `ODOO_ADMIN_USER` | Odoo admin user (XML-RPC) |
| `ODOO_ADMIN_PASSWORD` | Odoo admin password |
| `DB_HOST` | DW PostgreSQL host |
| `DB_PORT` | DW PostgreSQL port (default: 5432) |
| `DB_USER` | DW PostgreSQL user |
| `DB_PASSWORD` | DW PostgreSQL password |
| `DB_NAME` | DW database name |

## Usage

```bash
# Standard run (defaults to 7 days ago)
make run-prod-crm-stages

# From a specific date
make run-prod-crm-stages SINCE=2026-03-13
```

> In the monthly workflow, `--since` is explicitly set to 14 days ago.

## Target table

`raw.stage_changes`

| Column | Description |
|---|---|
| `opp_id` | Odoo opportunity ID |
| `opportunite` | Opportunity name |
| `client` | Client name |
| `commercial` | Odoo user ID of the salesperson |
| `etape_avant` | Stage before the change |
| `etape_apres` | Stage after the change |
| `date_changement` | Date of the change |
| `montant` | Opportunity amount at that point in time |

Conflict key: `(opp_id, date_changement, etape_avant, etape_apres)`
