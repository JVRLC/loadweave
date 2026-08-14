import re
import unicodedata
from datetime import datetime

# Pattern: YYMMDD_métaG_CLIENT_PRODUIT.xlsx
_FILENAME_RE = re.compile(
    r"(\d{6})_m[eé]ta[Gg]_([A-Z0-9]+)_([A-Z0-9]+)\.xlsx",
    re.IGNORECASE,
)

# Pattern: YYMMDD_SEQstart-end  (IGATech batch folder)
# Also handles SEQ1175-SEQ1277 style (second SEQ prefix optional)
_BATCH_RE = re.compile(r"(\d{6})_SEQ(\d+)[-_](?:SEQ)?(\d+)", re.IGNORECASE)


def _sanitize_batch_id(folder_name: str) -> str:
    """
    Produce a safe batch_id (max 64 chars) from any folder name.
    Standard folders (YYMMDD_SEQx-y) are returned as-is (truncated if needed).
    Non-standard folders are prefixed with MISC_ and spaces/accents cleaned.
    """
    if _BATCH_RE.search(folder_name):
        return folder_name[:64]
    normalized = unicodedata.normalize("NFD", folder_name)
    ascii_str = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    sanitized = re.sub(r"[^A-Za-z0-9_-]", "_", ascii_str).strip("_")
    sanitized = re.sub(r"_+", "_", sanitized)
    return f"MISC_{sanitized}"[:64]


def extract_batch_info(folder_name: str) -> dict:
    """
    Extract batch metadata from an IGATech folder name.
    e.g. '231004_SEQ112-157'
    Non-standard folders get a MISC_-prefixed sanitized batch_id.
    """
    batch_id = _sanitize_batch_id(folder_name)
    info = {
        "batch_id": batch_id,
        "seq_date": None,
        "seq_range_start": None,
        "seq_range_end": None,
        "prestataire": "IGATech",
    }
    m = _BATCH_RE.search(folder_name)
    if m:
        date_str, start, end = m.groups()
        try:
            info["seq_date"] = datetime.strptime(date_str, "%y%m%d").date()
        except ValueError:
            pass
        info["seq_range_start"] = int(start)
        info["seq_range_end"] = int(end)
    return info


def extract_sample_meta_from_filename(filename: str) -> dict:
    """
    Extract client / product / date from a contract xlsx filename.
    e.g. '230413_métaG_POG_MYCAUDIT.xlsx'
    """
    meta = {
        "client_code": None,
        "product_type": None,
        "sample_date": None,
    }
    m = _FILENAME_RE.search(filename)
    if m:
        date_str, client, product = m.groups()
        try:
            meta["sample_date"] = datetime.strptime(date_str, "%y%m%d").date()
        except ValueError:
            pass
        meta["client_code"] = client.upper()
        meta["product_type"] = product.upper()
    return meta


def infer_sample_type(path: str) -> str:
    """Infer sample type (sol / racines) from folder path."""
    path_lower = path.lower()
    if "racine" in path_lower:
        return "racines"
    if "sol" in path_lower:
        return "sol"
    return None
