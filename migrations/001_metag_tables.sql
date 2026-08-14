-- Migration 001 : Tables métagénomique (CMA / métabarcoding)

CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.metag_batch (
    batch_id        VARCHAR(64) PRIMARY KEY,
    seq_date        DATE,
    seq_range_start INTEGER,
    seq_range_end   INTEGER,
    prestataire     VARCHAR(64) DEFAULT 'IGATech',
    otu_table_path  TEXT,
    loaded_at       TIMESTAMP DEFAULT NOW(),
    source          VARCHAR(32) DEFAULT 'sharepoint'
);

CREATE TABLE IF NOT EXISTS raw.metag_sample (
    sample_id         VARCHAR(32) PRIMARY KEY,
    batch_id          VARCHAR(64) REFERENCES raw.metag_batch(batch_id),
    client_code       VARCHAR(32),
    product_type      VARCHAR(32),
    culture           VARCHAR(128),
    localisation      VARCHAR(256),
    country           VARCHAR(64) DEFAULT 'France',
    latitude          DOUBLE PRECISION,
    longitude         DOUBLE PRECISION,
    sample_date       DATE,
    sample_type       VARCHAR(32),
    dna_concentration DOUBLE PRECISION,
    loaded_at         TIMESTAMP DEFAULT NOW(),
    source            VARCHAR(32) DEFAULT 'sharepoint'
);

CREATE TABLE IF NOT EXISTS raw.metag_otu_abundance (
    id                  BIGSERIAL PRIMARY KEY,
    sample_id           VARCHAR(32) REFERENCES raw.metag_sample(sample_id),
    batch_id            VARCHAR(64) REFERENCES raw.metag_batch(batch_id),
    otu_id              VARCHAR(64),
    taxonomy_raw        TEXT,
    taxon_kingdom       VARCHAR(128),
    taxon_phylum        VARCHAR(128),
    taxon_class         VARCHAR(128),
    taxon_order         VARCHAR(128),
    taxon_family        VARCHAR(128),
    taxon_genus         VARCHAR(128),
    taxon_species       VARCHAR(256),
    abundance_absolute  INTEGER DEFAULT 0,
    abundance_relative  DOUBLE PRECISION DEFAULT 0,
    is_ama              BOOLEAN DEFAULT FALSE,
    loaded_at           TIMESTAMP DEFAULT NOW(),
    source              VARCHAR(32) DEFAULT 'sharepoint',
    UNIQUE (sample_id, batch_id, otu_id)
);

CREATE INDEX IF NOT EXISTS idx_metag_otu_sample    ON raw.metag_otu_abundance (sample_id);
CREATE INDEX IF NOT EXISTS idx_metag_otu_batch     ON raw.metag_otu_abundance (batch_id);
CREATE INDEX IF NOT EXISTS idx_metag_otu_genus     ON raw.metag_otu_abundance (taxon_genus);
CREATE INDEX IF NOT EXISTS idx_metag_otu_ama       ON raw.metag_otu_abundance (is_ama) WHERE is_ama = TRUE;
CREATE INDEX IF NOT EXISTS idx_metag_sample_client ON raw.metag_sample (client_code);
CREATE INDEX IF NOT EXISTS idx_metag_sample_batch  ON raw.metag_sample (batch_id);