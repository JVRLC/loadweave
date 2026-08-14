CREATE SCHEMA IF NOT EXISTS raw;

-- Annual targets by salesperson, sector and customer
CREATE TABLE IF NOT EXISTS raw.sales_targets (
    id                      SERIAL PRIMARY KEY,

    year                    INTEGER     NOT NULL,
    salesperson_id          VARCHAR     NOT NULL,   -- salesperson code (JND, BP, JL...)
    sector                  VARCHAR     NOT NULL,   -- sector (Vigne, Maraichage, PPAM, Gazon-EV, Arbo...)
    customer_name           VARCHAR     NOT NULL,   -- customer name

    -- Customer attributes
    country                 VARCHAR,
    segment                 VARCHAR,
    agronomy_engineer       VARCHAR,
    potential               VARCHAR,
    strategy                VARCHAR,
    confidence_level        NUMERIC,    -- confidence level (1 to 5)

    -- Annual targets (k EUR)
    annual_order_target     NUMERIC,    -- planned signature for the year
    annual_revenue_target   NUMERIC,    -- planned invoicing for the year

    -- Breakdown of annual_order_target by business origin
    deployment_share        NUMERIC,
    reengagement_share      NUMERIC,
    prospection_share       NUMERIC,

    -- Contracts (can be numeric amounts or status labels like START, PULSE)
    contract_previous_year  VARCHAR,
    contract_current_year   VARCHAR,

    _loaded_at              TIMESTAMP,
    _source                 VARCHAR,

    UNIQUE (year, salesperson_id, sector, customer_name)
);

CREATE INDEX IF NOT EXISTS idx_sales_targets_year_salesperson
    ON raw.sales_targets (year, salesperson_id);

CREATE INDEX IF NOT EXISTS idx_sales_targets_year_sector
    ON raw.sales_targets (year, sector);

CREATE INDEX IF NOT EXISTS idx_sales_targets_customer
    ON raw.sales_targets (customer_name);

-- Monthly target breakdown
CREATE TABLE IF NOT EXISTS raw.sales_targets_monthly (
    id              SERIAL PRIMARY KEY,

    year            INTEGER     NOT NULL,
    salesperson_id  VARCHAR     NOT NULL,
    sector          VARCHAR     NOT NULL,
    customer_name   VARCHAR     NOT NULL,
    period          VARCHAR(3)  NOT NULL,   -- P01 .. P12

    order_amount    NUMERIC,    -- planned signature target for this period (k EUR)
    revenue_amount  NUMERIC,    -- planned invoicing target for this period (k EUR)

    _loaded_at      TIMESTAMP,
    _source         VARCHAR,

    UNIQUE (year, salesperson_id, sector, customer_name, period)
);

CREATE INDEX IF NOT EXISTS idx_stm_year_salesperson
    ON raw.sales_targets_monthly (year, salesperson_id);

CREATE INDEX IF NOT EXISTS idx_stm_year_sector
    ON raw.sales_targets_monthly (year, sector);

CREATE INDEX IF NOT EXISTS idx_stm_customer
    ON raw.sales_targets_monthly (customer_name);

CREATE INDEX IF NOT EXISTS idx_stm_period
    ON raw.sales_targets_monthly (period);
