import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from loaders.weather_loader.history.api_client import OpenMeteoClient
from loaders.weather_loader.history.config import METEO_LOCATIONS

logger = logging.getLogger(__name__)


class MeteoExtractor:
    def __init__(self):
        self.client = OpenMeteoClient()

    def extract_location(self, location, start_date, end_date):
        """Helper function to extract data for a single location"""
        try:
            return self.client.get_historical_data(
                latitude=location["latitude"],
                longitude=location["longitude"],
                location_name=location["name"],
                code_pra=location.get("code"),
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as e:
            logger.error(f"Error extracting {location['name']}: {e}")
            return []

    def extract_all_locations(
        self, start_date: datetime = None, end_date: datetime = None
    ):
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()

        all_data = []
        logger.info(
            f"Extracting weather data from {start_date.date()} to {end_date.date()}"
        )

        total = len(METEO_LOCATIONS)
        max_workers = 10  # Parallelize 10 requests at a time

        logger.info(f"Starting parallel extraction with {max_workers} workers...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_loc = {
                executor.submit(self.extract_location, loc, start_date, end_date): loc
                for loc in METEO_LOCATIONS
            }

            # Process results as they complete
            completed = 0
            for future in as_completed(future_to_loc):
                loc = future_to_loc[future]
                completed += 1
                try:
                    data = future.result()
                    all_data.extend(data)
                    if completed % 10 == 0 or completed == total:
                        logger.info(f"  → Progress: [{completed}/{total}] locations processed")
                except Exception as e:
                    logger.error(f"Task failed for {loc['name']}: {e}")

        logger.info(f"✓ Total: {len(all_data)} records extracted")
        self.client.close()
        return all_data

    def get_locations(self):
        return self.client.get_locations()
