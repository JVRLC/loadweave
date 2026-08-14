# Démarrage

## Prérequis

- Docker + Docker Compose
- Python 3.10+
- Accès aux sources (Odoo, SharePoint, Aurea)

## Installation

### 1. Cloner le dépôt

```bash
git clone <repo>
cd data-loaders
```

### 2. Configurer l'environnement

```bash
cp .env.example .env.prod
```

Remplir `.env.prod` avec les variables nécessaires :

```bash
# Base de données
DB_NAME=db
DB_USER=myuser
DB_PASSWORD=mypassword
DB_HOST=db
DB_PORT=5432

# Odoo
ODOO_URL=https://your-company.odoo.com
ODOO_DB=your-database
ODOO_USERNAME=user@your-company.com
ODOO_PASSWORD=...

# SharePoint
SHAREPOINT_TENANT_ID=...
SHAREPOINT_CLIENT_ID=...
SHAREPOINT_CLIENT_SECRET=...
SHAREPOINT_SITE_URL=...

# Sample results → Supabase
SUPABASE_URL=...
SUPABASE_API_KEY=...

# Physico-chimique
PC_PROVIDER=aurea   # aurea | bdd_pc | esdac
AUREA_LOGIN=...
AUREA_PASSWORD=...
```

### 3. Build

=== "Production"

    ```bash
    make build-prod
    ```

=== "Développement"

    ```bash
    make build-dev
    ```

### 4. Initialiser la base de données

```bash
make init-prod-db
```

Applique les migrations SQL dans `migrations/`.

## Lancer un loader

Voir la page [Commandes Make](reference/commands.md) pour la liste complète.

```bash
# Exemple : loader business en prod
make up SERVICE=business ENV=prod
```

## Déploiement

`business`, `crm-stages` et les exports tournent automatiquement via des
**deployments Prefect**. Les planifications, l'historique des exécutions et les logs
sont consultables dans l'interface Prefect. Les variables d'environnement et les
secrets nécessaires aux flows doivent être configurés dans Prefect.

Les autres loaders (`weather-history`, `weather-daily`, `pc` (physico-chimique),
`metabarcoding`, `sales-pipeline`, `sample-results`) n'ont pas encore de planification automatisée :
ils se lancent manuellement en prod via `make up`, voir la page
[Commandes Make](reference/commands.md).

```bash
make up SERVICE=weather-daily ENV=prod
make up SERVICE=pc ENV=prod PC_PROVIDER=aurea
make up SERVICE=sales-pipeline ENV=prod
make up SERVICE=sample-results ENV=prod
```
