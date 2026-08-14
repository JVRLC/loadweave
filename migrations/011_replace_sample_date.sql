-- Migration 011 : Remplace sample_date par date_envoi + date_reception
-- et ajoute product_type dans upsert_sample_metadata (déjà présent en schéma).

ALTER TABLE raw.metag_sample
    RENAME COLUMN sample_date TO date_envoi;

ALTER TABLE raw.metag_sample
    ADD COLUMN IF NOT EXISTS date_reception DATE;
