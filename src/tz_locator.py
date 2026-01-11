import json
import os
import random
import pytz
import logging
from datetime import datetime
from .constants import DB_PATH
from .data_aggregator import download_geonames, aggregate_data

# Configure logging to output to the console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def build_database(force=False):
    logger.info(f"Starting database build (Force={force})...")
    try:
        download_geonames(force=force)
        logger.info("GeoNames download complete. Starting aggregation...")
        aggregate_data(force=force)
        logger.info("Database aggregation successful. world_cities.json is ready.")
    except Exception as e:
        logger.error(f"Database build failed: {str(e)}")

def get_cities(hour: int, population: int):
    if not os.path.exists(DB_PATH):
        build_database()

    with open(DB_PATH, "r", encoding="utf-8") as f:
        tz_map = json.load(f)

    now_utc = datetime.now(pytz.utc)
    winners = []

    for tz_id, locations in tz_map.items():
        try:
            tz = pytz.timezone(tz_id)
            local_time = now_utc.astimezone(tz)
            
            # Filter by the requested hour
            if local_time.hour == hour:
                # Get current abbreviation (e.g., CEST, PST) and UTC Offset (e.g., +0200)
                tz_abbreviation = local_time.strftime('%Z')
                utc_offset = local_time.strftime('%z')
                
                for loc in locations:
                    if loc['population'] >= population:
                        loc_with_time = loc.copy()
                        loc_with_time['local_time_str'] = local_time.strftime("%I:%M %p")
                        loc_with_time['timezone_id'] = tz_id
                        loc_with_time['timezone_abbr'] = tz_abbreviation
                        loc_with_time['utc_offset'] = utc_offset
                        winners.append(loc_with_time)
        except Exception:
            continue
    return winners

def get_cities_until_found(hour: int, population: int):
    cities = get_cities(hour, population)
    if not cities and population > 10:
        return get_cities_until_found(hour, int(population * 0.9))
    return cities, population

def pick_random_city(hour: int, population: int):
    cities, final_pop = get_cities_until_found(hour, population)
    if not cities: 
        return None, population
    return random.choice(cities), final_pop

def cities_to_json(data):
    return json.dumps(data, indent=4)