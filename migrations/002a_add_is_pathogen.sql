-- Migration 002 : ajout colonne is_pathogen dans metag_otu_abundance

ALTER TABLE raw.metag_otu_abundance
    ADD COLUMN IF NOT EXISTS is_pathogen BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_metag_otu_pathogen
    ON raw.metag_otu_abundance (is_pathogen)
    WHERE is_pathogen = TRUE;
