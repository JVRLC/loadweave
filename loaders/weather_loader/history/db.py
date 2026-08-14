import logging
from datetime import datetime
from sqlalchemy import text
from loaders.weather_loader.history.config import DB_SCHEMA, DB_TABLE
from loaders.db import get_engine

logger = logging.getLogger(__name__)

_COLS = [
    "latitude", "longitude", "location_name", "code_pra",
    "date_debut_releve", "date_fin_releve", "mois_observe", "annee_observee",
    "temperature_min_moyenne", "temperature_max_moyenne", "precipitation_moyenne",
    "coefficient_kc", "vitesse_max_moyenne_vent", "rayonnement_solaire_moyen",
    "loaded_at",
]
_CONFLICT_COLS = {"location_name", "annee_observee", "mois_observe"}
_UPDATE_COLS = [c for c in _COLS if c not in _CONFLICT_COLS]

_INSERT_SQL = text(f"""
    INSERT INTO {DB_SCHEMA}.{DB_TABLE} ({", ".join(_COLS)})
    VALUES ({", ".join(f":{c}" for c in _COLS)})
    ON CONFLICT (location_name, annee_observee, mois_observe)
    DO UPDATE SET {", ".join(f"{c} = EXCLUDED.{c}" for c in _UPDATE_COLS)}
""")


def create_meteo_table(engine):
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.{DB_TABLE} (
                id SERIAL PRIMARY KEY,
                latitude FLOAT, longitude FLOAT,
                location_name VARCHAR(255) NOT NULL,
                code_pra VARCHAR(50),
                date_debut_releve DATE, date_fin_releve DATE,
                mois_observe INT, annee_observee INT,
                temperature_min_moyenne FLOAT, temperature_max_moyenne FLOAT,
                precipitation_moyenne FLOAT, coefficient_kc FLOAT,
                vitesse_max_moyenne_vent FLOAT, rayonnement_solaire_moyen FLOAT,
                loaded_at TIMESTAMP
            )
        """))

    try:
        with engine.begin() as conn:
            conn.execute(text(f"""
                ALTER TABLE {DB_SCHEMA}.{DB_TABLE}
                ADD CONSTRAINT unique_weather_data_entry
                UNIQUE (location_name, annee_observee, mois_observe)
            """))
    except Exception as e:
        if "already exists" not in str(e):
            print(f"⚠ Warning: Could not add unique constraint: {e}")

    print(f"✓ Table {DB_SCHEMA}.{DB_TABLE} ready (with unique constraint)")


def insert_meteo_data(engine, data_list):
    if not data_list:
        return 0

    create_meteo_table(engine)

    with engine.begin() as conn:
        for d in data_list:
            params = {c: (datetime.now() if c == "loaded_at" else getattr(d, c)) for c in _COLS}
            conn.execute(_INSERT_SQL, params)

    print(f"✓ {len(data_list)} records inserted")
    return len(data_list)


def create_pra_table(engine):
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.pra (
                code_pra VARCHAR(10) PRIMARY KEY,
                name VARCHAR(255),
                latitude FLOAT,
                longitude FLOAT
            )
        """))
    print(f"✓ Table {DB_SCHEMA}.pra ready")


def load_pra_data(engine, pra_list):
    if not pra_list:
        return 0

    create_pra_table(engine)

    inserted = 0
    with engine.begin() as conn:
        for pra in pra_list:
            result = conn.execute(
                text(f"""
                    INSERT INTO {DB_SCHEMA}.pra (code_pra, name, latitude, longitude)
                    VALUES (:code, :name, :lat, :lon)
                    ON CONFLICT (code_pra) DO NOTHING
                """),
                {"code": pra["code"], "name": pra["name"], "lat": pra["latitude"], "lon": pra["longitude"]},
            )
            inserted += result.rowcount

    print(f"✓ {inserted} PRA records inserted")
    return inserted


class DbLoader:
    def __init__(self):
        self.engine = get_engine()

    def load_meteo_data(self, meteo_data) -> int:
        if not meteo_data:
            logger.warning("No data to load")
            return 0
        try:
            inserted = insert_meteo_data(self.engine, meteo_data)
            logger.info("✓ %d records loaded", inserted)
            return inserted
        except Exception as e:
            logger.error("Error loading data: %s", e)
            raise

    def load_pra_data(self, pra_list):
        try:
            logger.info("Loading PRA data...")
            inserted = load_pra_data(self.engine, pra_list)
            logger.info("✓ %d PRA records loaded", inserted)
            return inserted
        except Exception as e:
            logger.error("Error loading PRA data: %s", e, exc_info=True)
            raise

    def close(self):
        if self.engine:
            self.engine.dispose()
