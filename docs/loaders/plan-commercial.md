# Commercial Plan (sales pipeline)

Loads the current sales pipeline from a SharePoint Excel file into PostgreSQL.

## Table

| Table | Strategy | Content |
|---|---|---|
| `raw.commercial_plan` | full_replace | Sales pipeline opportunities, including monthly billing targets |

## Source file (SharePoint)

```
09_DATA/AA_Public/03_Reporting/Business/Plan commercial_Fin *.xlsx
```

- Sheet: `Base ouverte`
- Header row: row 3 (index 2)

## Columns

| Column | Excel Source | Description |
|---|---|---|
| `opportunity_name` | Opportunité | Opportunity name |
| `salesperson` | Vendeur | Sales representative responsible for the opportunity |
| `country` | Pays | Country |
| `expected_close_date` | Date de clôture prévue | Expected closing date |
| `contract_type` | Offre commerciale | Contract type |
| `target_value` | Valeur considérée | Opportunity amount |
| `sector` | Secteur d'activité 2 | Business sector |
| `billing_target_YYYY_MM` | Columns K to AH (one per month, header = first day of the month) | Billing target for that opportunity for the given month |

Rows without an `opportunity_name` are ignored.

## Run

```bash
make up SERVICE=sales-pipeline ENV=prod
```
