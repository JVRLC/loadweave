# Sample Results Loader

Synchronise la BDD Production CQ (SharePoint Excel) vers Supabase (`sample_results`).

## Source

```
04_PRODUCTION/10_QUALITE/001_ Analyse CQ/01_ Protocoles et outils/02_Base de données/
  BDD_Production CQ.xlsx
```

- Feuille : `échantillons et résultats`
- Filtre : lignes `Mix` / `MIX` avec `Date création ech` > 2025-01-01
- Mapping `lot_id` via table Supabase `lots.external_id`

## Cible

| Table Supabase | Stratégie |
|---|---|
| `sample_results` | upsert sur `external_id_usable` |

## Variables d'environnement

En plus des credentials SharePoint (`SHAREPOINT_*`) :

| Variable | Description |
|---|---|
| `SUPABASE_URL` | URL du projet Supabase |
| `SUPABASE_API_KEY` | Clé API (service role ou anon selon RLS) |
| `SAMPLE_RESULTS_FOLDER_PATH` | Override du dossier SharePoint (optionnel) |
| `SAMPLE_RESULTS_EXCEL_FILENAME` | Override du nom de fichier (optionnel) |

## Lancer

```bash
make up SERVICE=sample-results ENV=prod
```
