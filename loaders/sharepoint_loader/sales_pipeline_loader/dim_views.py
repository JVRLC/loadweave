import logging

from sqlalchemy import text

from loaders.db import get_engine

logger = logging.getLogger(__name__)

# PowerBI views dependent on raw.commercial_plan (see docs/powerbi_dim_views.md).
# A DROP TABLE ... CASCADE on commercial_plan removes them: we recreate them here
# just after reloading the table.
_VIEWS = {
    "dim.commercial": """
        CREATE OR REPLACE VIEW dim.commercial AS
        SELECT
            ROW_NUMBER() OVER (ORDER BY name) AS id,
            name
        FROM (
            SELECT DISTINCT CASE WHEN UPPER(salesperson) = UPPER('Mathilde Clément') THEN 'Mathilde Clément' ELSE salesperson END AS name
            FROM raw.commercial_plan WHERE salesperson IS NOT NULL
            UNION
            SELECT DISTINCT CASE WHEN UPPER(user_id) = UPPER('Mathilde Clément') THEN 'Mathilde Clément' ELSE user_id END
            FROM raw.opportunities WHERE user_id IS NOT NULL
        ) t
    """,
    "dim.sector": """
        CREATE OR REPLACE VIEW dim.sector AS
        SELECT
            ROW_NUMBER() OVER (ORDER BY name) AS id,
            name
        FROM (
            SELECT DISTINCT CASE WHEN UPPER(sector) = 'PPAM' THEN 'PPAM' ELSE sector END AS name
            FROM raw.commercial_plan WHERE sector IS NOT NULL
            UNION
            SELECT DISTINCT CASE WHEN UPPER(x_myco_sector_id) = 'PPAM' THEN 'PPAM' ELSE x_myco_sector_id END
            FROM raw.opportunities WHERE x_myco_sector_id IS NOT NULL
        ) t
    """,
    "dim.country": """
        CREATE OR REPLACE VIEW dim.country AS
        SELECT ROW_NUMBER() OVER (ORDER BY name) AS id, name
        FROM (
            SELECT DISTINCT country AS name FROM raw.commercial_plan WHERE country IS NOT NULL
            UNION
            SELECT DISTINCT CASE x_myco_inoculation_country_id
                WHEN 'Belgium'       THEN 'Belgique'
                WHEN 'Morocco'       THEN 'Maroc'
                WHEN 'Netherlands'   THEN 'Pays-Bas'
                WHEN 'Poland'        THEN 'Pologne'
                WHEN 'Romania'       THEN 'Roumanie'
                WHEN 'Spain'         THEN 'Espagne'
                WHEN 'Switzerland'   THEN 'Suisse'
                WHEN 'Ireland'       THEN 'Irlande'
                WHEN 'Senegal'       THEN 'Sénégal'
                WHEN 'United States' THEN 'États-Unis'
                ELSE x_myco_inoculation_country_id
            END FROM raw.opportunities WHERE x_myco_inoculation_country_id IS NOT NULL
        ) t
    """,
    "dim.contract_type": """
        CREATE OR REPLACE VIEW dim.contract_type AS
        SELECT ROW_NUMBER() OVER (ORDER BY name) AS id, name
        FROM (
            SELECT DISTINCT
                CASE LOWER(contract_type)
                    WHEN 'pulse - upsell' THEN 'pulse_upsell'
                    ELSE LOWER(contract_type)
                END AS name
            FROM raw.commercial_plan WHERE contract_type IS NOT NULL
            UNION
            SELECT DISTINCT LOWER(x_myco_contract_type)
            FROM raw.opportunities WHERE x_myco_contract_type IS NOT NULL
        ) t
    """,
}


def recreate_dim_views():
    engine = get_engine()
    with engine.begin() as conn:
        for view_name, sql in _VIEWS.items():
            conn.execute(text(sql))
            logger.info("✓ Recreated view %s", view_name)
    engine.dispose()
