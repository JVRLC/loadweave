# Commandes Make

Liste de toutes les commandes disponibles via `make`.

## Build

| Commande | Description |
|---|---|
| `make build-dev` | Build l'image Docker de développement |
| `make build-prod` | Build l'image Docker de production |

## Base de données

| Commande | Description |
|---|---|
| `make init-dev-db` | Applique les migrations SQL de bootstrap (dev) |
| `make init-prod-db` | Applique les migrations SQL de bootstrap (prod) |

## Loaders

Cible générique unique : `make up SERVICE=<name> [ENV=dev\|prod] [PC_PROVIDER=aurea\|bdd_pc\|esdac]`.
`ENV` vaut `dev` par défaut. `PC_PROVIDER` n'est requis que pour `SERVICE=pc`.

Services disponibles : `weather-history`, `weather-daily`, `business`, `stock`, `pc`, `metabarcoding`, `sales-pipeline`, `sample-results`.

| Commande | Description |
|---|---|
| `make up SERVICE=business ENV=dev` | Business loader (Odoo) en dev |
| `make up SERVICE=business ENV=prod` | Business loader (Odoo) en prod |
| `make up SERVICE=stock ENV=dev` | Stock loader (Odoo) en dev |
| `make up SERVICE=stock ENV=prod` | Stock loader (Odoo) en prod |
| `make up SERVICE=weather-history ENV=dev` | Weather history loader en dev |
| `make up SERVICE=weather-daily ENV=dev` | Weather daily loader en dev |
| `make up SERVICE=pc ENV=prod PC_PROVIDER=aurea` | Loader physico-chimique Aurea en prod |
| `make up SERVICE=pc ENV=prod PC_PROVIDER=bdd_pc` | Loader physico-chimique BDD_PC en prod |
| `make up SERVICE=sales-pipeline ENV=prod` | Plan commercial (sales pipeline) en prod |
| `make up SERVICE=sample-results ENV=prod` | Sample results (CQ → Supabase) en prod |
| `make run-prod-metabarcoding` | Métabarcoding loader en prod (Python direct) |
| `make run-prod-crm-stages` | CRM stage changes loader en prod |

## Utilitaires

| Commande | Description |
|---|---|
| `make down` | Arrête tous les containers |
| `make clean` | Supprime containers, images et volumes |
| `make export-donnees-source` | Export données source |
| `make export-reporting-mensuel` | Export reporting mensuel |

## Syntaxe cron — référence

| Expression | Description |
|---|---|
| `0 * * * *` | Toutes les heures |
| `0 6 * * *` | Tous les jours à 6h |
| `0 0 * * 0` | Tous les dimanches à minuit |
| `0 7 * * 1` | Tous les lundis à 7h |
| `*/30 * * * *` | Toutes les 30 minutes |
