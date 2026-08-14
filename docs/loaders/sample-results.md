# Sample Results (CQ Production)

Charge les résultats d'échantillons Mix depuis SharePoint vers Supabase.

## Tables

| Table Supabase | Stratégie | Contenu |
|---|---|---|
| `sample_results` | upsert (`external_id_usable`) | Spores/g, morphotypes F/M/m/a/A, contrôle qualité |
| `lots` (lecture) | — | Résolution de `lot_id` via `external_id` |

## Source (SharePoint)

```
04_PRODUCTION/10_QUALITE/001_ Analyse CQ/01_ Protocoles et outils/02_Base de données/
  BDD_Production CQ.xlsx
```

- Feuille : `échantillons et résultats`
- Filtre : `Mix` / `MIX`, date création > 2025-01-01

## Colonnes cibles

| Colonne | Source Excel |
|---|---|
| `sampling_date` | Date création ech |
| `result` | Résultat (spores/g) |
| `F`, `M`, `m`, `a`, `A` | Morphotypes |
| `quality_control` | Etape de contrôle qualité (normalisé : S+6 → S_6, …) |
| `external_id` | Code lot (plan MIX paddé à 6 avec `x` + D/L), ex. `CRR2xx#D01-L01` |
| `lot_id` | Lookup `lots.external_id` |
| `external_id_usable` | `external_id` + index ligne (clé d'upsert) |

## Variables d'environnement

| Variable | Description |
|---|---|
| `SHAREPOINT_TENANT_ID` / `CLIENT_ID` / `CLIENT_SECRET` / `SITE_URL` | Auth Graph |
| `SUPABASE_URL` | URL projet Supabase |
| `SUPABASE_API_KEY` | Clé API Supabase |
| `SAMPLE_RESULTS_FOLDER_PATH` | Override du dossier SharePoint (optionnel) |
| `SAMPLE_RESULTS_EXCEL_FILENAME` | Override du nom de fichier (optionnel) |

## Lancer

```bash
make up SERVICE=sample-results ENV=prod
```
