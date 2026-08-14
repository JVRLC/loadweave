# Pipeline Métabarcoding — Diagrammes

## Schéma DB

```mermaid
erDiagram
    metag_batch {
        VARCHAR batch_id PK
        DATE seq_date
        INTEGER seq_range_start
        INTEGER seq_range_end
        VARCHAR prestataire
        VARCHAR otu_table_path
        TIMESTAMP _loaded_at
    }
    metag_sample {
        VARCHAR sample_id PK
        VARCHAR batch_id FK
        VARCHAR client_code
        VARCHAR product_type
        VARCHAR culture
        VARCHAR localisation
        VARCHAR country
        DOUBLE latitude
        DOUBLE longitude
        DATE sample_date
        VARCHAR sample_type
        DOUBLE dna_concentration
        TIMESTAMP _loaded_at
    }
    metag_otu_abundance {
        BIGSERIAL id PK
        VARCHAR sample_id FK
        VARCHAR batch_id FK
        VARCHAR otu_id
        TEXT taxonomy_raw
        VARCHAR taxon_kingdom
        VARCHAR taxon_phylum
        VARCHAR taxon_class
        VARCHAR taxon_order
        VARCHAR taxon_family
        VARCHAR taxon_genus
        VARCHAR taxon_species
        INTEGER abundance_absolute
        DOUBLE abundance_relative
        BOOLEAN is_ama
        BOOLEAN is_pathogen
        TIMESTAMP _loaded_at
        VARCHAR _source
    }
    metag_batch ||--o{ metag_sample : batch_id
    metag_sample ||--o{ metag_otu_abundance : sample_id
```

---

## Source 1 — IGATech (batches Amplicon ITS)

```mermaid
flowchart TD
    SP["SharePoint\nIGATech_Rawdata/YYMMDD_SEQx-y/"]
    REF["REF SEQ IGATECH.xlsx\n1701 entrées"]

    SP -->|list_files depth 1-3| OTU["otu_table_*_L7.txt\n~16000 OTUs × N samples"]
    REF -->|build_ref_lookup| LOOKUP["dict SEQxxx → metadata"]

    OTU -->|Passe 1 — totaux| TOTALS["total reads / sample"]
    OTU -->|"Passe 2 — chunks 2000 OTUs"| PARSE["parse taxonomie QIIME\nk__ p__ c__ o__ f__ g__ s__"]

    PARSE --> PHYLUM["taxon_phylum"]
    PARSE --> GENUS["taxon_genus"]
    TOTALS --> ABREL["abundance_relative\n= count / total"]

    PHYLUM --> AMA{"Glomeromycota ?"}
    AMA -->|oui| IS_AMA["is_ama = TRUE"]
    AMA -->|non| NOT_AMA["is_ama = FALSE"]

    GENUS --> PATH{"genre in\n54 pathogènes Marion ?"}
    PATH -->|oui| IS_PATH["is_pathogen = TRUE"]
    PATH -->|non| NOT_PATH["is_pathogen = FALSE"]

    LOOKUP -->|lookup_sample_meta| META["culture, lat/lon,\nlocalisation, sample_type"]

    IS_AMA & NOT_AMA & IS_PATH & NOT_PATH & ABREL & META --> DB

    DB[("raw.metag_batch\nraw.metag_sample\nraw.metag_otu_abundance\n_source = sharepoint")]
```

**Incrémental** : `batch_already_loaded()` skip les batches déjà en base.
**16S skippés** : dossiers contenant `_16s_` / `16sonly` ignorés.

---

## Pipeline 2 passes (IGATech)

```mermaid
flowchart TD
    FILE["Fichier OTU .tsv\n~16000 lignes × 108 colonnes"]

    FILE -->|Passe 1 — Totaux par échantillon| PASS1
    subgraph PASS1["Passe 1"]
        direction LR
        S1["SEQ021 = 45230 séq."]
        S2["SEQ022 = 38910 séq."]
    end

    FILE -->|"Passe 2 — Chunks de 2000 OTUs"| PARSE
    PARSE["Découpe taxonomie QIIME"]
    PARSE --> GENUS["genre extrait"]
    PARSE --> PHYLUM["phylum extrait"]

    PHYLUM --> AMA{"phylum ==\nGlomeromycota ?"}
    AMA -->|oui| IS_AMA_T["is_ama = TRUE"]
    AMA -->|non| IS_AMA_F["is_ama = FALSE"]
    GENUS --> PATH{"genre in\n54 pathogènes Marion ?"}
    PATH -->|oui| IS_PATH_T["is_pathogen = TRUE"]
    PATH -->|non| IS_PATH_F["is_pathogen = FALSE"]

    PASS1 --> ABREL["abundance_relative\n= count / total"]

    IS_AMA_T & IS_AMA_F & IS_PATH_T & IS_PATH_F & ABREL --> DB[("raw.metag_otu_abundance")]
```

---

## Logique de classification taxonomique

```mermaid
flowchart LR
    RAW["k__Fungi;p__Glomeromycota;\ng__Rhizophagus;s__irregularis"]

    RAW --> K["taxon_kingdom\nFungi"]
    RAW --> P["taxon_phylum\nGlomeromycota"]
    RAW --> G["taxon_genus\nRhizophagus"]
    RAW --> S["taxon_species\nirregularis"]

    P --> AMA{"phylum ==\nGlomeromycota ?"}
    AMA -->|oui| AMA_T["is_ama = TRUE"]
    AMA -->|non| AMA_F["is_ama = FALSE"]

    G --> PATH{"genre in\n54 Pathogènes (liste Marion) ?"}
    PATH -->|oui| PATH_T["is_pathogen = TRUE"]
    PATH -->|non| PATH_F["is_pathogen = FALSE"]
```
