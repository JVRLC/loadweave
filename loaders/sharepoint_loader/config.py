import os
from dotenv import load_dotenv

load_dotenv()

# Central SharePoint credentials
SHAREPOINT_CONFIG = {
    "sharepoint_site_url": os.getenv("SHAREPOINT_SITE_URL"),
    "sharepoint_client_id": os.getenv("SHAREPOINT_CLIENT_ID"),
    "sharepoint_client_secret": os.getenv("SHAREPOINT_CLIENT_SECRET"),
    "sharepoint_tenant_id": os.getenv("SHAREPOINT_TENANT_ID"),
}

ALL_FILES_CONFIG = [
    # Metabarcoding loader — IGATech raw batches (OTU tables)
    {
        "folder_path": (
            "03_R&D INNOV/30_LABORATOIRE ANALYSES CONTRATS CQ"
            "/03_Métagénomique - Data & Traçabilité/IGATech_Rawdata"
        ),
        "loader": "metabarcoding_loader",
    },
    {
        "loader": "sales_pipeline_loader",
        "folder_path": "09_DATA/AA_Public/03_Reporting/Business",
    },
    # Sample results — BDD Production CQ → Supabase sample_results
    {
        "loader": "sample_results_loader",
        "folder_path": (
            "04_PRODUCTION/10_QUALITE/001_ Analyse CQ"
            "/01_ Protocoles et outils/02_Base de données"
        ),
        "excel_filename": "BDD_Production CQ.xlsx",
    },
]
