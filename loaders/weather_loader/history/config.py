from loaders.weather_loader.shared.pras_data import PRAS_LIST
from loaders.weather_loader.shared.pras_coordinates_fix import apply_coordinate_fixes

# Apply coordinate corrections to PRAS list
METEO_LOCATIONS = apply_coordinate_fixes(PRAS_LIST)

# API Endpoints:
# - NASA POWER: Agroclimatology (Monthly)
# - Docs: https://power.larc.nasa.gov/docs/services/api/temporal/monthly/
API_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
TIMEZONE = "Europe/Paris"
DB_SCHEMA = "raw"
DB_TABLE = "weather_data"
API_DELAY = 0.5  # Delay between API calls in seconds