import logging
import os

from loaders.sharepoint_loader.config import SHAREPOINT_CONFIG
from loaders.sharepoint_loader.shared.client import SharePointClient
from loaders.sharepoint_loader.metabarcoding_loader.tsv_parser import stream_otu_tsv
from loaders.sharepoint_loader.metabarcoding_loader.metadata_parser import (
    extract_batch_info,
    extract_sample_meta_from_filename,
    infer_sample_type,
)
from loaders.sharepoint_loader.metabarcoding_loader.db_loader import (
    batch_already_loaded,
    upsert_batch,
    upsert_samples,
    load_otu_abundance,
)
from loaders.sharepoint_loader.metabarcoding_loader.ref_seq_enricher import (
    build_ref_lookup,
    lookup_sample_meta,
    enrich_all_samples,
    REF_FILE_PATH,
)

logger = logging.getLogger(__name__)

RAWDATA_FOLDER = (
    "03_R&D INNOV/30_LABORATOIRE ANALYSES CONTRATS CQ"
    "/03_Métagénomique - Data & Traçabilité/IGATech_Rawdata"
)

# Priority order for OTU table filenames within a batch folder
OTU_FILE_PRIORITY = [
    "otu_table_sample-metadata_no-singletons_L7.txt",
    "otu_table_sample-metadata_no-singletons_L6.txt",
    "otu_table.tsv",
]

# Folder name fragments that indicate non-ITS batches (16S bacteria, etc.)
# These are skipped entirely — no fungal OTU data expected.
NON_ITS_MARKERS = ["16sonly", "_16s_", "_16s-"]


def _build_client() -> SharePointClient:
    client = SharePointClient.from_config(SHAREPOINT_CONFIG)
    client.authenticate()
    return client


def _pick_otu_file(items: list[dict]) -> dict | None:
    """Select the best OTU table file from a folder listing."""
    by_name = {item["name"]: item for item in items if "file" in item}
    for priority_name in OTU_FILE_PRIORITY:
        if priority_name in by_name:
            return by_name[priority_name]
    # Fallback: any file matching otu_table*.tsv or otu_table*.txt
    for item in items:
        name = item.get("name", "")
        if "file" in item and name.startswith("otu_table") and name.endswith((".tsv", ".txt")):
            return item
    return None


def _search_folder(
    client: SharePointClient, path: str, depth: int, max_depth: int = 3
) -> tuple[dict | None, str]:
    """Recursively look for an OTU table file inside `path`, up to `max_depth` levels deep."""
    try:
        items = client.list_files(path)
    except Exception:
        logger.debug("Could not list folder: %s", path)
        return None, ""

    logger.debug("Contents of %s: %s", path, [i["name"] for i in items])
    otu = _pick_otu_file(items)
    if otu:
        if depth > 0:
            logger.info("OTU table found at depth %d: %s", depth, path)
        return otu, path

    if depth >= max_depth:
        return None, ""

    for item in items:
        if "folder" not in item:
            continue
        otu, found_path = _search_folder(client, f"{path}/{item['name']}", depth + 1, max_depth)
        if otu:
            return otu, found_path

    return None, ""


def _find_otu_file(client: SharePointClient, batch_folder: str) -> tuple[dict | None, str]:
    """
    Search for an OTU table file up to 3 levels deep inside batch_folder.
    Returns (file_item, folder_path) or (None, "").
    """
    otu, path = _search_folder(client, batch_folder, depth=0)
    if otu:
        return otu, path

    # Nothing found anywhere — log a summary
    items = client.list_files(batch_folder)
    all_files = [i["name"] for i in items if "file" in i]
    all_subfolders = [i["name"] for i in items if "folder" in i]
    logger.warning(
        "No OTU table found in %s — files: %s | subfolders: %s",
        batch_folder, all_files, all_subfolders,
    )
    return None, ""


def process_batch(client: SharePointClient, batch_folder: str, batch_name: str,
                  ref_lookup: dict | None = None):
    batch_info = extract_batch_info(batch_name)

    if batch_already_loaded(batch_info["batch_id"]):
        logger.info("Batch %s already loaded, skipping", batch_info["batch_id"])
        return

    logger.info("Processing batch: %s", batch_info["batch_id"])

    otu_file, otu_folder = _find_otu_file(client, batch_folder)
    if not otu_file:
        return

    otu_path = f"{otu_folder}/{otu_file['name']}"
    batch_info["otu_table_path"] = otu_path

    logger.info("Downloading %s", otu_path)
    file_content = client.download_file(otu_path)

    sample_type = infer_sample_type(batch_folder)
    batch_id = batch_info["batch_id"]
    file_meta = extract_sample_meta_from_filename(otu_file["name"])

    upsert_batch(batch_info)

    samples_seen: set[str] = set()
    for chunk_df, sample_cols in stream_otu_tsv(file_content):
        if chunk_df.empty:
            continue

        # Upsert any new samples discovered in this chunk
        new_sample_ids = set(chunk_df["sample_id"].unique()) - samples_seen
        if new_sample_ids:
            new_samples = []
            for sid in new_sample_ids:
                # REF SEQ IGATECH est la seule source de vérité pour les métadonnées
                ref = lookup_sample_meta(sid, ref_lookup) if ref_lookup else {}
                new_samples.append({
                    "sample_id":         sid,
                    "batch_id":          batch_id,
                    "client_code":    ref.get("client_code") or file_meta.get("client_code"),
                    "product_type":   ref.get("product_type"),
                    "culture":        ref.get("culture"),
                    "localisation":   ref.get("localisation"),
                    "country":        "France",
                    "latitude":       ref.get("latitude"),
                    "longitude":      ref.get("longitude"),
                    "date_envoi":     ref.get("date_envoi"),
                    "date_reception": ref.get("date_reception"),
                    "sample_type":    ref.get("sample_type") or sample_type,
                })
            upsert_samples(new_samples)
            samples_seen.update(new_sample_ids)

        load_otu_abundance(chunk_df, batch_id)


def run():
    client = _build_client()

    # Charger le lookup REF SEQ une seule fois pour toute la pipeline
    logger.info("Loading REF SEQ IGATECH metadata...")
    try:
        ref_content = client.download_file(REF_FILE_PATH)
        ref_lookup = build_ref_lookup(ref_content)
    except Exception:
        logger.warning("Could not load REF SEQ file — samples will be inserted without metadata")
        ref_lookup = {}

    logger.info("Listing IGATech batch folders: %s", RAWDATA_FOLDER)
    batch_folders = [
        item for item in client.list_files(RAWDATA_FOLDER)
        if "folder" in item
    ]

    if not batch_folders:
        logger.warning("No batch folders found in %s", RAWDATA_FOLDER)
        return

    logger.info("Found %d batch folders", len(batch_folders))
    for folder in batch_folders:
        name = folder["name"]
        name_lower = name.lower()
        if any(marker in name_lower for marker in NON_ITS_MARKERS):
            logger.info("Skipping non-ITS batch (16S / bacteria): %s", name)
            continue
        folder_path = f"{RAWDATA_FOLDER}/{name}"
        try:
            process_batch(client, folder_path, name, ref_lookup)
        except Exception:
            logger.exception("Error processing batch %s", name)

    # Enrichissement final : couvre les samples historiques déjà en DB
    if ref_lookup:
        logger.info("Running final REF SEQ enrichment pass on all samples...")
        enrich_all_samples(ref_lookup)


if __name__ == "__main__":
    import os
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run()
