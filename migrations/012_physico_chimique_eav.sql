-- Migration 012 : Tables EAV pour les résultats physico-chimiques (schéma raw)
--
-- Modèle Entity-Attribute-Value avec 4 tables dans raw :
--   raw.pc_source       → prestataires & sources open source
--   raw.pc_echantillon  → métadonnées de chaque échantillon
--   raw.pc_parametre    → référentiel des paramètres mesurés
--   raw.pc_mesure       → valeurs EAV (une ligne par paramètre × échantillon)

CREATE SCHEMA IF NOT EXISTS raw;

-- ─────────────────────────────────────────────
-- 1. SOURCE
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw.pc_source (
    id          SMALLSERIAL  PRIMARY KEY,
    nom         VARCHAR(128) NOT NULL,
    type        VARCHAR(32)  NOT NULL
                    CHECK (type IN ('prestataire', 'open_source', 'interne')),
    description TEXT,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE (nom)
);

COMMENT ON TABLE  raw.pc_source         IS 'Prestataires d''analyse et sources open source';
COMMENT ON COLUMN raw.pc_source.type    IS 'prestataire | open_source | interne';

-- ─────────────────────────────────────────────
-- 2. ECHANTILLON
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw.pc_echantillon (
    id               BIGSERIAL    PRIMARY KEY,
    code_echantillon VARCHAR(64)  NOT NULL,  -- référence fournie par le laboratoire
    aurea_id         VARCHAR(32),             -- numresultat Aurea (traçabilité)
    date_prelevement DATE,
    localisation     TEXT,
    culture          VARCHAR(128),
    type_sol         VARCHAR(64),
    client_code      VARCHAR(64),
    source_id        SMALLINT     REFERENCES raw.pc_source(id) ON DELETE SET NULL,
    loaded_at        TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE (code_echantillon, source_id)
);

COMMENT ON TABLE  raw.pc_echantillon                   IS 'Métadonnées de chaque échantillon prélevé';
COMMENT ON COLUMN raw.pc_echantillon.code_echantillon  IS 'Identifiant unique de l''échantillon (ex: N° BDD_PC)';
COMMENT ON COLUMN raw.pc_echantillon.source_id         IS 'Source d''où provient la métadonnée (prestataire, interne…)';

-- ─────────────────────────────────────────────
-- 3. PARAMETRE
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw.pc_parametre (
    id            SERIAL       PRIMARY KEY,
    nom           VARCHAR(256) NOT NULL,
    nom_normalise VARCHAR(256) NOT NULL,
    categorie     VARCHAR(64),
    description   TEXT,
    UNIQUE (nom_normalise)
);

COMMENT ON TABLE  raw.pc_parametre                IS 'Référentiel de tous les paramètres physico-chimiques mesurés';
COMMENT ON COLUMN raw.pc_parametre.nom_normalise  IS 'Nom snake_case normalisé (clé technique)';
COMMENT ON COLUMN raw.pc_parametre.categorie      IS 'Ex: texture, macroelements, pH, matiere_organique…';

-- ─────────────────────────────────────────────
-- 4. MESURE  (EAV)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw.pc_mesure (
    id             BIGSERIAL        PRIMARY KEY,
    echantillon_id BIGINT           NOT NULL REFERENCES raw.pc_echantillon(id) ON DELETE CASCADE,
    parametre_id   INTEGER          NOT NULL REFERENCES raw.pc_parametre(id),
    source_id      SMALLINT         REFERENCES raw.pc_source(id) ON DELETE SET NULL,
    valeur         DOUBLE PRECISION,           -- valeur numérique
    valeur_texte   TEXT,                       -- valeur texte quand non numérique
    unite          VARCHAR(32),
    date_mesure    DATE,
    commentaire    TEXT,
    loaded_at      TIMESTAMP        NOT NULL DEFAULT NOW(),
    -- Un seul enregistrement par (échantillon, paramètre, source)
    UNIQUE (echantillon_id, parametre_id, source_id)
);

COMMENT ON TABLE  raw.pc_mesure               IS 'Table EAV : une ligne par valeur mesurée (paramètre × échantillon)';
COMMENT ON COLUMN raw.pc_mesure.valeur        IS 'Valeur numérique de la mesure';
COMMENT ON COLUMN raw.pc_mesure.valeur_texte  IS 'Valeur textuelle quand non convertible en nombre';
COMMENT ON COLUMN raw.pc_mesure.unite         IS 'Unité de la mesure (ex: mg/kg, %, µS/cm)';

-- ─────────────────────────────────────────────
-- INDEX
-- ─────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_pc_mesure_echantillon  ON raw.pc_mesure (echantillon_id);
CREATE INDEX IF NOT EXISTS idx_pc_mesure_parametre    ON raw.pc_mesure (parametre_id);
CREATE INDEX IF NOT EXISTS idx_pc_mesure_source       ON raw.pc_mesure (source_id);
CREATE INDEX IF NOT EXISTS idx_pc_mesure_date         ON raw.pc_mesure (date_mesure);
CREATE INDEX IF NOT EXISTS idx_pc_echantillon_code    ON raw.pc_echantillon (code_echantillon);
CREATE INDEX IF NOT EXISTS idx_pc_echantillon_date    ON raw.pc_echantillon (date_prelevement);
CREATE INDEX IF NOT EXISTS idx_pc_parametre_normalise ON raw.pc_parametre (nom_normalise);
CREATE INDEX IF NOT EXISTS idx_pc_parametre_categorie ON raw.pc_parametre (categorie);
