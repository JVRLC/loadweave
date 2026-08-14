CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.stage_changes (
    opp_id          INTEGER       NOT NULL,
    opportunite     TEXT,
    client          TEXT,
    commercial      INTEGER,
    etape_avant     TEXT,
    etape_apres     TEXT,
    date_changement TIMESTAMP     NOT NULL,
    montant         NUMERIC,
    CONSTRAINT uq_stage_changes UNIQUE (opp_id, date_changement, etape_avant, etape_apres)
);

CREATE INDEX IF NOT EXISTS idx_stage_changes_opp_id ON raw.stage_changes (opp_id);
CREATE INDEX IF NOT EXISTS idx_stage_changes_date   ON raw.stage_changes (date_changement);
