"""Sample results loader — SharePoint Excel → Supabase `sample_results`."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
import pandas as pd
import requests

from loaders.sharepoint_loader.config import ALL_FILES_CONFIG, SHAREPOINT_CONFIG
from loaders.sharepoint_loader.shared.client import SharePointClient
from loaders.sharepoint_loader.sample_results_loader.supabase import (
    map_lot_ids,
    upsert_sample_results,
)
from loaders.sharepoint_loader.sample_results_loader.transform import (
    SHEET_NAME,
    clean_excel,
    prepare_records,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

_CONFIG = next(f for f in ALL_FILES_CONFIG if f["loader"] == "sample_results_loader")
FOLDER_PATH = os.getenv("SAMPLE_RESULTS_FOLDER_PATH") or _CONFIG["folder_path"]
EXCEL_FILENAME = os.getenv("SAMPLE_RESULTS_EXCEL_FILENAME") or _CONFIG["excel_filename"]


def _build_client() -> SharePointClient:
    return SharePointClient.from_config(SHAREPOINT_CONFIG)


def run():
    logger.info("=== Sample Results Loader Started ===")
    logger.info("Script started at: %s", datetime.now().isoformat())

    client = _build_client()
    try:
        client.authenticate()
    except requests.HTTPError as e:
        raise RuntimeError(f"SharePoint authentication failed: {e}") from e

    logger.info("Searching for files in folder: %s", FOLDER_PATH)
    files = client.list_files(FOLDER_PATH)
    logger.info("Found %d files in SharePoint folder", len(files))

    excel_file = next((f for f in files if f.get("name") == EXCEL_FILENAME), None)
    if not excel_file:
        available = sorted(f.get("name") or "" for f in files)
        raise FileNotFoundError(
            f"The file {EXCEL_FILENAME!r} was not found in {FOLDER_PATH!r}. "
            f"Available: {available}"
        )

    file_path = f"{FOLDER_PATH}/{EXCEL_FILENAME}"
    logger.info("Downloading: %s", EXCEL_FILENAME)
    content = client.download_file(file_path)
    content.seek(0)

    raw = pd.read_excel(content, sheet_name=SHEET_NAME)
    logger.info("Successfully loaded Excel file with %d rows", len(raw))

    cleaned = clean_excel(raw)
    records = prepare_records(cleaned)
    records = map_lot_ids(records)

    logger.info("Preparing final data for upload...")
    n = upsert_sample_results(records)

    logger.info("=== Sample Results Loader Completed Successfully ===")
    logger.info("Uploaded %d records. Completed at: %s", n, datetime.now().isoformat())


if __name__ == "__main__":
    run()
