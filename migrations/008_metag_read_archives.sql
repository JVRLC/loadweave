CREATE TABLE IF NOT EXISTS raw.metag_read (
    id           BIGSERIAL PRIMARY KEY,
    batch_id     VARCHAR(64)  NOT NULL,
    sample_id    VARCHAR(128),
    file_name    VARCHAR(256),
    read_name    TEXT         NOT NULL,
    sequence     TEXT         NOT NULL,
    quality      TEXT,
    read_length  INTEGER      GENERATED ALWAYS AS (length(sequence)) STORED,
    read_pair    VARCHAR(4),                    -- R1, R2, ou NULL si single-end
    _loaded_at   TIMESTAMP    DEFAULT NOW(),
    _source      VARCHAR(32)  DEFAULT 'sharepoint'
);

CREATE INDEX IF NOT EXISTS idx_metag_read_batch
    ON raw.metag_read (batch_id);
CREATE INDEX IF NOT EXISTS idx_metag_read_sample
    ON raw.metag_read (sample_id);
