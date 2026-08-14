# SharePoint Excel Loader

Ce loader permet de récupérer des fichiers Excel depuis SharePoint et de les charger dans le schéma `raw` de la base de données.

## Configuration

Ajouter les variables suivantes dans le fichier `.env` :

```env
# SharePoint OAuth2 (Azure AD App Registration)
SHAREPOINT_TENANT_ID=votre-tenant-id
SHAREPOINT_CLIENT_ID=votre-client-id
SHAREPOINT_CLIENT_SECRET=votre-client-secret
SHAREPOINT_SITE_URL=https://company.sharepoint.com/sites/MySite

# Fichier à charger
SHAREPOINT_FILE_PATH=/Shared Documents/data/fichier.xlsx
SHAREPOINT_SHEET_NAME=Sheet1  # Optionnel

# Base de données
DB_SCHEMA=raw
SHAREPOINT_DB_TABLE=nom_table  # Optionnel, utilise le nom du fichier par défaut
```

## Prérequis Azure AD

1. Créer une **App Registration** dans Azure AD
2. Ajouter les permissions API Microsoft Graph :
   - `Sites.Read.All` (Application)
   - `Files.Read.All` (Application)
3. Accorder le consentement administrateur
4. Créer un **Client Secret**

## Utilisation

### En ligne de commande

```bash
cd /path/to/data-loaders
python -m loaders.sharepoint_loader.src.main
```

### En Python

```python
from loaders.sharepoint_loader.src.main import run_pipeline

# Utiliser la config par défaut (.env)
run_pipeline()

# Ou spécifier les paramètres
run_pipeline(
    file_path="/Shared Documents/reports/data.xlsx",
    sheet_name="Data",
    schema="raw",
    table_name="ma_table",
    if_exists="replace"  # ou "append"
)
```

### Lister les fichiers d'un dossier

```python
from loaders.sharepoint_loader.src.sharepoint_client import SharePointClient

client = SharePointClient()
client.authenticate()
files = client.list_files("/Shared Documents/data")
for f in files:
    print(f["name"])
```

## Dépendances

```
requests
pandas
openpyxl
python-dotenv
sqlalchemy
psycopg2-binary
```
