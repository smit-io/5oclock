import json
import os
import random
import sqlite3
from zoneinfo import ZoneInfo
import pytz
import logging
from datetime import datetime, timezone
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

def get_matching_iana_ids(cursor, target_hour):
    """Finds all IANA primary keys whose current local time matches the target hour."""
    cursor.execute("SELECT id, timezone_id FROM iana_timezones")
    all_tzs = cursor.fetchall()
    
    now_utc = datetime.now(timezone.utc)
    matching_ids = []
    
    for db_id, tz_str in all_tzs:
        try:
            # Calculate local hour for this specific TZ right now
            local_hour = now_utc.astimezone(ZoneInfo(tz_str)).hour
            if local_hour == target_hour:
                matching_ids.append(db_id)
        except Exception:
            continue
            
    return matching_ids

def get_all_cities(target_hour, min_pop, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tz_ids = get_matching_iana_ids(cursor, target_hour)
    if not tz_ids: return []

    placeholders = ','.join(['?'] * len(tz_ids))
    query = f"""
        SELECT l.city, l.state, l.country, l.population, t.timezone_id
        FROM locations l
        JOIN iana_timezones t ON l.iana_id = t.id
        WHERE l.iana_id IN ({placeholders}) AND l.population >= ?
        ORDER BY l.population DESC
    """
    cursor.execute(query, (*tz_ids, min_pop))
    return cursor.fetchall()

def get_all_cities_recursive(target_hour, min_pop, db_path, floor=500):
    """Recursively drops population by 10% until cities are found."""
    cities = get_all_cities(target_hour, min_pop, db_path)
    
    if not cities and min_pop > floor:
        new_pop = int(min_pop * 0.9)
        return get_all_cities_recursive(target_hour, new_pop, db_path, floor)
    
    return cities, min_pop

def get_random_city(target_hour, min_pop, db_path):
    """Gets a random city using the OFFSET method for O(1) performance."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Get current matching timezones
    tz_ids = get_matching_iana_ids(cursor, target_hour)
    if not tz_ids: return None, min_pop

    # 2. Recursive population check (Get count first)
    current_pop = min_pop
    total_count = 0
    placeholders = ','.join(['?'] * len(tz_ids))
    
    while total_count == 0 and current_pop >= 500:
        cursor.execute(f"SELECT COUNT(*) FROM locations WHERE iana_id IN ({placeholders}) AND population >= ?", (*tz_ids, current_pop))
        total_count = cursor.fetchone()[0]
        if total_count == 0:
            current_pop = int(current_pop * 0.9)

    if total_count == 0: return None, current_pop

    # 3. Pick a random index and fetch
    random_index = random.randint(0, total_count - 1)
    query = f"""
        SELECT l.city, l.state, l.country, l.population, t.timezone_id
        FROM locations l
        JOIN iana_timezones t ON l.iana_id = t.id
        WHERE l.iana_id IN ({placeholders}) AND l.population >= ?
        LIMIT 1 OFFSET ?
    """
    cursor.execute(query, (*tz_ids, current_pop, random_index))
    result = cursor.fetchone()
    
    # Format result to dict for FastAPI
    city_dict = {
        "city": result[0], "state": result[1], "country": result[2],
        "population": result[3], "timezone_id": result[4]
    }
    return city_dict, current_pop