import logging
import requests
import time
from datetime import date
from loaders.db import get_engine
from loaders.weather_loader.daily.db import insert_daily_data
from loaders.weather_loader.shared.pras_data import PRAS_LIST
from loaders.weather_loader.shared.pras_coordinates_fix import apply_coordinate_fixes

logger = logging.getLogger(__name__)

# Liste des variables à récupérer
VARIABLES = [
    "temperature_2m_min",
    "temperature_2m_max",
    "precipitation_sum",
    "windspeed_10m_max",
    "shortwave_radiation_sum",
    "sunshine_duration",
    "et0_fao_evapotranspiration"
]

API_URL = "https://api.open-meteo.com/v1/forecast"
TIMEZONE = "Europe/Paris"
API_DELAY = 0.5  # Délai entre les appels API

# Correction des coordonnées PRA
METEO_LOCATIONS = apply_coordinate_fixes(PRAS_LIST)

def fetch_daily_data(lat, lon, variables, target_date):
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join(variables),
        "start_date": target_date,
        "end_date": target_date,
        "timezone": TIMEZONE
    }
    response = requests.get(API_URL, params=params)
    response.raise_for_status()
    return response.json()

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    today = date.today().isoformat()
    all_data = []
    for pra in METEO_LOCATIONS:
        lat = pra["latitude"]
        lon = pra["longitude"]
        code_pra = pra["code"]
        data = fetch_daily_data(lat, lon, VARIABLES, today)
        # Formatage des données pour insertion en base (à adapter selon le schéma)
        if "daily" in data:
            daily = data["daily"]
            row = {
                "Code_PRA": code_pra,
                "Latitude": lat,
                "Longitude": lon,
                "date": today
            }
            for var in VARIABLES:
                if var in daily:
                    row[var] = daily[var][0] if daily[var] else None
            all_data.append(row)
        time.sleep(API_DELAY)

    engine = get_engine()
    insert_daily_data(engine, all_data)
    logger.info("✓ Données insérées pour %d PRA.", len(all_data))

if __name__ == "__main__":
    main()
