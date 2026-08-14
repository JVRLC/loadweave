-- Migration 010 : Supprime dna_concentration de raw.metag_sample
-- Colonne jamais renseignée (aucune source disponible).

ALTER TABLE raw.metag_sample DROP COLUMN IF EXISTS dna_concentration;
