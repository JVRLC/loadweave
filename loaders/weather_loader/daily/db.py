import logging
from datetime import datetime
from sqlalchemy import text

logger = logging.getLogger(__name__)

DB_SCHEMA = "raw"
DB_TABLE = "weather_data_daily"

_COLS = [
    "code_pra", "latitude", "longitude", "date",
    "temperature_2m_min", "temperature_2m_max", "precipitation_sum",
    "windspeed_10m_max", "shortwave_radiation_sum", "sunshine_duration",
    "et0_fao_evapotranspiration", "loaded_at",
]
_CONFLICT_COLS = {"code_pra", "date"}
_UPDATE_COLS = [c for c in _COLS if c not in _CONFLICT_COLS]

_INSERT_SQL = text(f"""
    INSERT INTO {DB_SCHEMA}.{DB_TABLE} ({", ".join(_COLS)})
    VALUES ({", ".join(f":{c}" for c in _COLS)})
    ON CONFLICT (code_pra, date)
    DO UPDATE SET {", ".join(f"{c} = EXCLUDED.{c}" for c in _UPDATE_COLS)}
""")


def create_daily_table(engine):
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.{DB_TABLE} (
                id SERIAL PRIMARY KEY,
                code_pra VARCHAR(50),
                latitude FLOAT, longitude FLOAT,
                date DATE,
                temperature_2m_min FLOAT, temperature_2m_max FLOAT,
                precipitation_sum FLOAT, windspeed_10m_max FLOAT,
                shortwave_radiation_sum FLOAT, sunshine_duration FLOAT,
                et0_fao_evapotranspiration FLOAT,
                loaded_at TIMESTAMP
            )
        """))

    try:
        with engine.begin() as conn:
            conn.execute(text(f"""
                ALTER TABLE {DB_SCHEMA}.{DB_TABLE}
                ADD CONSTRAINT unique_weather_data_daily_entry
                UNIQUE (code_pra, date)
            """))
    except Exception as e:
        if "already exists" not in str(e):
            logger.warning("Could not add unique constraint: %s", e)

    logger.info("✓ Table %s.%s ready (with unique constraint)", DB_SCHEMA, DB_TABLE)


def insert_daily_data(engine, data_list):
    if not data_list:
        return 0
    create_daily_table(engine)

    with engine.begin() as conn:
        for d in data_list:
            params = {
                "code_pra":                   d.get("Code_PRA"),
                "latitude":                   d.get("Latitude"),
                "longitude":                  d.get("Longitude"),
                "date":                       d.get("date"),
                "temperature_2m_min":         d.get("temperature_2m_min"),
                "temperature_2m_max":         d.get("temperature_2m_max"),
                "precipitation_sum":          d.get("precipitation_sum"),
                "windspeed_10m_max":          d.get("windspeed_10m_max"),
                "shortwave_radiation_sum":    d.get("shortwave_radiation_sum"),
                "sunshine_duration":          d.get("sunshine_duration"),
                "et0_fao_evapotranspiration": d.get("et0_fao_evapotranspiration"),
                "loaded_at":                  datetime.now(),
            }
            conn.execute(_INSERT_SQL, params)

    logger.info("✓ %d records inserted", len(data_list))
    return len(data_list)
