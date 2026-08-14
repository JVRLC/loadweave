import os
import re
import logging

import requests

from loaders.sharepoint_loader.config import ALL_FILES_CONFIG, SHAREPOINT_CONFIG
from loaders.sharepoint_loader.shared.client import SharePointClient
from loaders.sharepoint_loader.shared.db_loader import load_to_raw_full_replace
from loaders.sharepoint_loader.sales_pipeline_loader.parser import parse_pipeline
from loaders.sharepoint_loader.sales_pipeline_loader.dim_views import recreate_dim_views

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

TABLE = "commercial_plan"
FILE_PATTERN = re.compile(r"Plan commercial_Fin .+\.xlsx", re.IGNORECASE)

_CONFIG = next(f for f in ALL_FILES_CONFIG if f["loader"] == "sales_pipeline_loader")
FOLDER_PATH = _CONFIG["folder_path"]


def _build_client() -> SharePointClient:
    return SharePointClient.from_config(SHAREPOINT_CONFIG)


def run():
    schema = os.getenv("DB_SCHEMA", "raw")
    client = _build_client()

    try:
        client.authenticate()
    except requests.HTTPError as e:
        raise RuntimeError(f"SharePoint authentication failed: {e}") from e

    files = client.list_files(FOLDER_PATH)
    pipeline_files = [f for f in files if FILE_PATTERN.search(f.get("name", ""))]

    if not pipeline_files:
        logger.warning("No 'Plan commercial_Fin *.xlsx' file found in '%s'", FOLDER_PATH)
        return

    for file_info in pipeline_files:
        file_name = file_info["name"]
        file_path = f"{FOLDER_PATH}/{file_name}"
        logger.info("Downloading: %s", file_name)

        try:
            file_content = client.download_file(file_path)
        except requests.HTTPError as e:
            logger.error("Download failed for '%s': %s", file_name, e)
            continue

        df = parse_pipeline(file_content)
        if df is None or df.empty:
            logger.warning("No data extracted from '%s'", file_name)
            continue

        load_to_raw_full_replace(df, schema, TABLE)
        logger.info("✓ %d rows -> %s.%s", len(df), schema, TABLE)

        recreate_dim_views()


if __name__ == "__main__":
    run()
