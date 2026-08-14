ALTER TABLE raw.metag_batch
    RENAME COLUMN loaded_at TO _loaded_at;
ALTER TABLE raw.metag_batch
    RENAME COLUMN source TO _source;

ALTER TABLE raw.metag_sample
    RENAME COLUMN loaded_at TO _loaded_at;
ALTER TABLE raw.metag_sample
    RENAME COLUMN source TO _source;

ALTER TABLE raw.metag_otu_abundance
    RENAME COLUMN loaded_at TO _loaded_at;
ALTER TABLE raw.metag_otu_abundance
    RENAME COLUMN source TO _source;
