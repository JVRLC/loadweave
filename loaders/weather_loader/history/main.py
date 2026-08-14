import logging
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from loaders.weather_loader.history.extractor import MeteoExtractor
from loaders.weather_loader.history.db import DbLoader

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main(start_date: datetime = None, end_date: datetime = None):
    try:
        logger.info("Starting meteorological data loading")
        logger.info("\n[1/2] EXTRACTING from NASA POWER API...")
        extractor = MeteoExtractor()
        meteo_data = extractor.extract_all_locations(start_date, end_date)

        if not meteo_data:
            logger.warning("No data extracted")
            return False

        logger.info("\n[2/2] LOADING to PostgreSQL (raw.weather_data)...")
        loader = DbLoader()
        loaded_count = loader.load_meteo_data(meteo_data)
        loader.close()

        logger.info(f"✓ Pipeline completed successfully!")
        logger.info(f"  - Extracted: {len(meteo_data)} records")
        logger.info(f"  - Loaded: {loaded_count} records")

        return True

    except Exception as e:
        logger.error(f"\n✗ Error during execution: {e}", exc_info=True)
        return False


if __name__ == "__main__":

    # Example: Load data from Jan 1, 2014 to 7 days ago
    start = datetime.strptime("2014-01-01", "%Y-%m-%d")
    end = datetime.now() - timedelta(days=7)

    success = main(start_date=start, end_date=end)
    sys.exit(0 if success else 1)
