import csv
import gc
import pandas as pd
from io import BytesIO, StringIO
from typing import Generator

# CMA detection: all Glomeromycota are arbuscular mycorrhizal fungi (confirmed by Greg)

# Genera of plant-pathogenic fungi — validated by Marion (2026-03-30)
# Source: https://ephytia.inrae.fr/fr/C/26472/Hypp
PATHOGEN_GENERA = {
    # Existing / well-known
    "fusarium", "rhizoctonia", "pythium", "phytophthora", "sclerotinia",
    "verticillium", "botrytis", "alternaria", "gaeumannomyces", "plasmodiophora",
    "colletotrichum", "pyrenophora", "septoria", "puccinia", "blumeria",
    "erysiphe", "magnaporthe", "sclerotium", "macrophomina", "thielaviopsis",
    # Validated by Marion
    "chondrostereum", "cicinobolus", "claviceps", "cristulariella",
    "didymella", "diplocarpon", "exobasidium", "fomitopsis",
    "guignardia", "helicobasidium", "heterobasidion", "kabatiella",
    "leptosphaeria", "leveillula", "marasmius", "monilinia",
    "ophiostoma", "peyronellaea", "phomopsis", "phragmidium",
    "podosphaera", "rhytisma", "rosellinia", "sphacelotheca",
    "sporisorium", "stromatinia", "taphrina", "thanatephorus",
    "tilletia", "tranzschelia", "uromyces", "urocystis",
    "ustilago", "venturia",
}


def _extract_header_and_data(raw: str) -> tuple[str, str]:
    """Split raw file text into (header_line, data_text)."""
    lines = raw.splitlines()
    header_line = None
    data_lines = []
    for line in lines:
        stripped = line.lstrip("#").strip()
        if not header_line and (
            stripped.startswith("OTU ID")
            or stripped.startswith("observation_name")
            or stripped.startswith("observation name")
        ):
            header_line = stripped
            continue
        if line.startswith("#") or not line.strip():
            continue
        data_lines.append(line)
    if not header_line:
        raise ValueError("OTU table: header row not found")
    return header_line, "\n".join(data_lines)


def _parse_taxonomy_dict(taxonomy_str) -> dict:
    """Parse QIIME-style string → dict of taxon levels."""
    levels = [
        "taxon_kingdom", "taxon_phylum", "taxon_class",
        "taxon_order", "taxon_family", "taxon_genus", "taxon_species",
    ]
    prefixes = ["k__", "p__", "c__", "o__", "f__", "g__", "s__"]
    result = {l: None for l in levels}

    if not isinstance(taxonomy_str, str):
        return result

    for part in taxonomy_str.replace("; ", ";").split(";"):
        part = part.strip()
        for prefix, level in zip(prefixes, levels):
            if part.startswith(prefix):
                value = part[len(prefix):].strip()
                if value and value not in ("", "uncultured", "unidentified", "Unknown"):
                    result[level] = value
                break
    return result


def _process_chunk(rows: list[dict], headers: list[str], first_col: str,
                   taxonomy_col: str | None, sample_cols: list[str],
                   sample_totals: dict[str, int]) -> pd.DataFrame:
    records = []
    for row in rows:
        otu_id = row[first_col]
        tax_raw = row.get(taxonomy_col) if taxonomy_col else None
        tax = _parse_taxonomy_dict(tax_raw)
        genus = (tax.get("taxon_genus") or "").lower()

        for s in sample_cols:
            try:
                count = int(float(row.get(s) or 0))
            except (ValueError, TypeError):
                count = 0
            if count == 0:
                continue
            total = sample_totals.get(s) or 1
            records.append({
                "otu_id": otu_id,
                "sample_id": s,
                "taxonomy_raw": tax_raw,
                **tax,
                "abundance_absolute": count,
                "abundance_relative": round(count / total, 6),
                "is_ama": tax.get("taxon_phylum") == "Glomeromycota",
                "is_pathogen": genus in PATHOGEN_GENERA,
            })
    return pd.DataFrame(records) if records else pd.DataFrame()


def stream_otu_tsv(
    file_content: BytesIO,
    chunk_size: int = 2000,
) -> Generator[tuple[pd.DataFrame, list[str]], None, None]:
    """
    Memory-efficient generator: yields (chunk_df, sample_ids) tuples.

    Two-pass strategy:
      Pass 1 — compute per-sample read totals (needed for relative abundance).
      Pass 2 — stream OTU rows in chunk_size batches, yield long-format DataFrames.

    Peak memory ≈ file_text_size + chunk_size × n_samples × ~200 bytes.
    """
    raw = file_content.read().decode("utf-8", errors="replace")
    header_line, data_text = _extract_header_and_data(raw)
    del raw

    headers = next(csv.reader([header_line], delimiter="\t"))
    first_col = headers[0]
    taxonomy_col = next(
        (h for h in headers if h.lower() in ("taxonomy", "classification")), None
    )
    exclude = {first_col}
    if taxonomy_col:
        exclude.add(taxonomy_col)
    sample_cols = [h for h in headers if h not in exclude]

    # Pass 1: per-sample totals
    sample_totals: dict[str, int] = {s: 0 for s in sample_cols}
    for row in csv.DictReader(StringIO(data_text), fieldnames=headers, delimiter="\t"):
        for s in sample_cols:
            try:
                sample_totals[s] += int(float(row.get(s) or 0))
            except (ValueError, TypeError):
                pass

    # Pass 2: stream in chunks
    buffer: list[dict] = []
    total_otus = 0
    for row in csv.DictReader(StringIO(data_text), fieldnames=headers, delimiter="\t"):
        buffer.append(row)
        total_otus += 1
        if len(buffer) >= chunk_size:
            chunk_df = _process_chunk(buffer, headers, first_col,
                                      taxonomy_col, sample_cols, sample_totals)
            yield chunk_df, sample_cols
            buffer.clear()
            gc.collect()

    if buffer:
        chunk_df = _process_chunk(buffer, headers, first_col,
                                  taxonomy_col, sample_cols, sample_totals)
        yield chunk_df, sample_cols

    del data_text
    gc.collect()
    print(f"✓ OTU table streamed: {total_otus} OTUs, {len(sample_cols)} samples")
