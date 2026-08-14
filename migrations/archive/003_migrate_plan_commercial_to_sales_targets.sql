-- Migration: Rename plan_commercial tables to sales_targets
-- This migration renames columns and copies data from old schema to new schema

BEGIN TRANSACTION;

-- Migrate data from plan_commercial to sales_targets
INSERT INTO raw.sales_targets (
    year,
    salesperson_id,
    sector,
    customer_name,
    country,
    segment,
    agronomy_engineer,
    potential,
    strategy,
    confidence_level,
    annual_order_target,
    annual_revenue_target,
    deployment_share,
    reengagement_share,
    prospection_share,
    contract_previous_year,
    contract_current_year,
    _loaded_at,
    _source
)
SELECT
    annee,
    commercial,
    filiere,
    client,
    pays,
    segment,
    inge_agro,
    potentiel,
    strategie,
    niveau_confiance,
    objectif_sig,
    objectif_fact,
    part_deploiement,
    part_relance,
    part_prospection,
    contrat_annee_precedente,
    contrat_annee,
    _loaded_at,
    _source
FROM raw.plan_commercial
ON CONFLICT (year, salesperson_id, sector, customer_name)
DO UPDATE SET
    country = EXCLUDED.country,
    segment = EXCLUDED.segment,
    agronomy_engineer = EXCLUDED.agronomy_engineer,
    potential = EXCLUDED.potential,
    strategy = EXCLUDED.strategy,
    confidence_level = EXCLUDED.confidence_level,
    annual_order_target = EXCLUDED.annual_order_target,
    annual_revenue_target = EXCLUDED.annual_revenue_target,
    deployment_share = EXCLUDED.deployment_share,
    reengagement_share = EXCLUDED.reengagement_share,
    prospection_share = EXCLUDED.prospection_share,
    contract_previous_year = EXCLUDED.contract_previous_year,
    contract_current_year = EXCLUDED.contract_current_year,
    _loaded_at = EXCLUDED._loaded_at,
    _source = EXCLUDED._source;

-- Migrate data from plan_commercial_periode to sales_targets_monthly
INSERT INTO raw.sales_targets_monthly (
    year,
    salesperson_id,
    sector,
    customer_name,
    period,
    order_amount,
    revenue_amount,
    _loaded_at,
    _source
)
SELECT
    annee,
    commercial,
    filiere,
    client,
    periode,
    sig_montant,
    fact_montant,
    _loaded_at,
    _source
FROM raw.plan_commercial_periode
ON CONFLICT (year, salesperson_id, sector, customer_name, period)
DO UPDATE SET
    order_amount = EXCLUDED.order_amount,
    revenue_amount = EXCLUDED.revenue_amount,
    _loaded_at = EXCLUDED._loaded_at,
    _source = EXCLUDED._source;

-- Drop old tables after successful migration
DROP TABLE IF EXISTS raw.plan_commercial_periode;
DROP TABLE IF EXISTS raw.plan_commercial;

COMMIT;
