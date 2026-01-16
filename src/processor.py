from collections import deque
from datetime import datetime, timezone
import random
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

import pytz
from src.constants import GEONAMES_DB_PATH, CITIES_DB_PATH, FORCE_UPDATE
from src.timezone_finder import find_best_matching_timezones_with_meta

def should_process_cities() -> bool:
    """Checks if cities.db needs to be (re)generated."""
    if FORCE_UPDATE or not CITIES_DB_PATH.exists():
        return True
    return GEONAMES_DB_PATH.stat().st_mtime > CITIES_DB_PATH.stat().st_mtime

def sanitize_table_name(name: str) -> str:
    """Converts IANA timezone names into valid SQLite table names."""
    # Replace slashes, dashes, and spaces with underscores
    clean_name = re.sub(r'[^a-zA-Z0-9]', '_', name).lower()
    return f"tz_{clean_name}"

def process_refined_data():
    if not should_process_cities():
        print("Refined database 'cities.db' is already up to date.")
        return

    print("Generating refined 'cities.db' with timezone grouping...")
    
    conn = sqlite3.connect(CITIES_DB_PATH)
    cursor = conn.cursor()
    
    # 1. Reset Tables
    cursor.execute("DROP TABLE IF EXISTS iana_timezones")
    cursor.execute("DROP TABLE IF EXISTS cities")
    
    cursor.execute("""
        CREATE TABLE iana_timezones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timezone_name TEXT UNIQUE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            state TEXT,
            country TEXT,
            population INTEGER,
            latitude REAL,
            longitude REAL,
            state_abbr TEXT,
            country_abbr TEXT,
            timezone_id INTEGER,
            FOREIGN KEY (timezone_id) REFERENCES iana_timezones (id)
        )
    """)

    # 2. Attach the raw geonames database
    cursor.execute(f"ATTACH DATABASE '{GEONAMES_DB_PATH}' AS raw")

    # 3. Get all unique timezones from raw data
    cursor.execute("SELECT DISTINCT timezone FROM raw.cities WHERE timezone IS NOT NULL ORDER BY timezone")
    timezones = [row[0] for row in cursor.fetchall()]

    # 4. Process each timezone one by one
    for tz_name in timezones:
        # Insert timezone and get its new ID
        cursor.execute("INSERT INTO iana_timezones (timezone_name) VALUES (?)", (tz_name,))
        tz_id = cursor.lastrowid
        
        print(f"Processing timezone: {tz_name}...")

        # Insert cities for THIS timezone, sorted by population DESC
        # Note: We use CAST for population to ensure numerical sorting
        cursor.execute("""
            INSERT INTO cities (
                name, state, country, population, latitude, longitude, 
                state_abbr, country_abbr, timezone_id
            )
            SELECT 
                c.name,
                a.name AS state,
                co.country AS country,
                CAST(c.population AS INTEGER) as pop,
                CAST(c.latitude AS REAL),
                CAST(c.longitude AS REAL),
                c.admin1_code AS state_abbr,
                c.country_code AS country_abbr,
                ?
            FROM raw.cities c
            LEFT JOIN raw.country_info co ON c.country_code = co.iso
            LEFT JOIN raw.admin_codes a ON (c.country_code || '.' || c.admin1_code) = a.code
            WHERE c.timezone = ? AND CAST(c.population AS INTEGER) > 0
            ORDER BY pop DESC
        """, (tz_id, tz_name))

    conn.commit()
    cursor.execute("DETACH DATABASE raw")
    conn.close()
    print(f"Successfully created refined database at {CITIES_DB_PATH}")

def create_timezone_specific_tables(force: bool = False):
    """
    Creates a separate table for every timezone in iana_timezones.
    Original 'cities' and 'iana_timezones' tables are preserved.
    """
    conn = sqlite3.connect(CITIES_DB_PATH)
    cursor = conn.cursor()

    # 1. Get all timezones to loop through
    cursor.execute("SELECT id, timezone_name FROM iana_timezones")
    timezones = cursor.fetchall()

    print(f"Starting fan-out to {len(timezones)} specific tables...")

    for tz_id, tz_name in timezones:
        table_name = sanitize_table_name(tz_name)
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        exists = cursor.fetchone()

        if exists and not force:
            continue

        # 2. Drop if force flag is active
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

        # 3. Create the specialized table
        # We don't need the timezone_id column here since it's implicit in the table name
        cursor.execute(f"""
            CREATE TABLE {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                state TEXT,
                country TEXT,
                population INTEGER,
                latitude REAL,
                longitude REAL,
                state_abbr TEXT,
                country_abbr TEXT
            )
        """)

        # 4. Insert data from the master 'cities' table
        cursor.execute(f"""
            INSERT INTO {table_name} (
                name, state, country, population, latitude, longitude, state_abbr, country_abbr
            )
            SELECT 
                name, state, country, population, latitude, longitude, state_abbr, country_abbr
            FROM cities
            WHERE timezone_id = ?
            ORDER BY population DESC
        """, (tz_id,))

    conn.commit()
    conn.close()
    print("Timezone-specific tables generated successfully.")
    
def get_top_populated_cities(limit: int = 10) -> List[Tuple]:
    """Returns the top X most populated cities across the whole world."""
    conn = sqlite3.connect(CITIES_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, state, country, population, latitude, longitude, state_abbr, country_abbr, timezone_id 
        FROM cities 
        ORDER BY population DESC 
        LIMIT ?
    """, (limit,))
    results = cursor.fetchall()
    conn.close()
    return results

def get_cities_by_population_range(min_pop: int, max_pop: int) -> List[Tuple]:
    """Returns cities within a specific population bracket."""
    conn = sqlite3.connect(CITIES_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, state, country, population, latitude, longitude, state_abbr, country_abbr, timezone_id 
        FROM cities 
        WHERE population BETWEEN ? AND ?
        ORDER BY population DESC
    """, (min_pop, max_pop))
    results = cursor.fetchall()
    conn.close()
    return results

def save_query_to_table(table_name: str, data: List[Tuple], force: bool = False):
    """
    Creates a new table and inserts provided data while 
    maintaining Foreign Key relationships to iana_timezones.
    """
    if not data:
        print(f"No data provided for table '{table_name}'. Skipping.")
        return

    conn = sqlite3.connect(CITIES_DB_PATH)
    # Crucial: SQLite needs this per-connection to enforce constraints
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    exists = cursor.fetchone()

    if exists and not force:
        print(f"Table '{table_name}' already exists. Use force=True to overwrite.")
        conn.close()
        return

    print(f"Creating table '{table_name}' with FK integrity...")
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    
    # Updated CREATE TABLE with Foreign Key reference
    cursor.execute(f"""
        CREATE TABLE {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            state TEXT,
            country TEXT,
            population INTEGER,
            latitude REAL,
            longitude REAL,
            state_abbr TEXT,
            country_abbr TEXT,
            timezone_id INTEGER,
            FOREIGN KEY (timezone_id) REFERENCES iana_timezones (id)
        )
    """)

    # Insert the data
    placeholders = ", ".join(["?"] * len(data[0]))
    cursor.executemany(f"""
        INSERT INTO {table_name} (
            name, state, country, population, latitude, longitude, 
            state_abbr, country_abbr, timezone_id
        ) VALUES ({placeholders})
    """, data)
    
    conn.commit()
    conn.close()
    print(f"Table '{table_name}' is ready and linked to iana_timezones.")
    
def get_top_populated_cities(limit: int = 10) -> List[Tuple]:
    """Returns the top X most populated cities across the whole world."""
    conn = sqlite3.connect(CITIES_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, state, country, population, latitude, longitude, state_abbr, country_abbr, timezone_id 
        FROM cities 
        ORDER BY population DESC 
        LIMIT ?
    """, (limit,))
    results = cursor.fetchall()
    conn.close()
    return results

def get_cities_by_population_range(min_pop: int, max_pop: int, limit: int) -> List[Dict[str, Any]]:
    """
    Returns cities within a population bracket, including 
    live timezone metadata (local time, date, and abbreviation).
    """
    conn = sqlite3.connect(CITIES_DB_PATH)
    cursor = conn.cursor()
    
    # We join with iana_timezones to get the timezone_name instead of just the ID
    query = """
        SELECT 
            c.name, c.state, c.country, c.population, 
            c.latitude, c.longitude, c.state_abbr, c.country_abbr,
            t.timezone_name
        FROM cities c
        JOIN iana_timezones t ON c.timezone_id = t.id
        WHERE c.population BETWEEN ? AND ?
        ORDER BY c.population DESC
        LIMIT ?
    """
    
    cursor.execute(query, (min_pop, max_pop, limit))
    rows = cursor.fetchall()
    conn.close()

    # Get current UTC time once to use as a baseline for all results
    now_utc = datetime.now(timezone.utc)
    refined_results = []

    for row in rows:
        tz_name = row[8] # timezone_name from the JOIN
        
        try:
            # Generate live time data for this specific city
            tz = pytz.timezone(tz_name)
            local_now = now_utc.astimezone(tz)
            
            refined_results.append({
                "name": row[0],
                "state": row[1],
                "country": row[2],
                "population": row[3],
                "latitude": row[4],
                "longitude": row[5],
                "state_abbr": row[6],
                "country_abbr": row[7],
                "timezone": tz_name,
                "local_date": local_now.strftime("%Y-%m-%d"),
                "local_time": local_now.strftime("%H:%M:%S"),
                "timezone_abbr": local_now.strftime("%Z")
            })
        except Exception:
            # Fallback if a timezone name is somehow invalid
            continue

    return refined_results

def save_query_to_table(table_name: str, data: List[Tuple], force: bool = False):
    """
    Creates a new table and inserts provided data.
    If force is True, it drops the table first.
    """
    if not data:
        print(f"No data provided for table '{table_name}'. Skipping.")
        return

    conn = sqlite3.connect(CITIES_DB_PATH)
    cursor = conn.cursor()

    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    exists = cursor.fetchone()

    if exists and not force:
        print(f"Table '{table_name}' already exists. Use force=True to overwrite.")
        conn.close()
        return

    print(f"Creating table '{table_name}' with {len(data)} records...")
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    
    # Create table with the same structure as the results we are passing
    cursor.execute(f"""
        CREATE TABLE {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            state TEXT,
            country TEXT,
            population INTEGER,
            latitude REAL,
            longitude REAL,
            state_abbr TEXT,
            country_abbr TEXT,
            timezone_id INTEGER
        )
    """)

    # Insert the data
    placeholders = ", ".join(["?"] * len(data[0]))
    cursor.executemany(f"INSERT INTO {table_name} (name, state, country, population, latitude, longitude, state_abbr, country_abbr, timezone_id) VALUES ({placeholders})", data)
    
    conn.commit()
    conn.close()
    print(f"Table '{table_name}' is ready.")
    
def get_top_cities_per_timezone(limit_per_tz: int = 5) -> List[Tuple]:
    """
    Returns the top X most populated cities for EVERY timezone.
    Uses a Window Function to rank cities within their timezone group.
    """
    conn = sqlite3.connect(CITIES_DB_PATH)
    cursor = conn.cursor()
    
    # We use a Subquery (CTE) to rank cities, then filter by that rank
    query = """
    WITH RankedCities AS (
        SELECT 
            name, state, country, population, latitude, longitude, 
            state_abbr, country_abbr, timezone_id,
            ROW_NUMBER() OVER (
                PARTITION BY timezone_id 
                ORDER BY population DESC
            ) as rank
        FROM cities
    )
    SELECT name, state, country, population, latitude, longitude, state_abbr, country_abbr, timezone_id
    FROM RankedCities
    WHERE rank <= ?
    ORDER BY timezone_id, population DESC
    """
    
    cursor.execute(query, (limit_per_tz,))
    results = cursor.fetchall()
    conn.close()
    return results

def get_cities_range_per_timezone(min_pop: int, max_pop: int) -> List[Tuple]:
    """
    Returns cities within a population range, grouped by timezone.
    This ensures that even in the result list, cities from the same 
    timezone stay together.
    """
    conn = sqlite3.connect(CITIES_DB_PATH)
    cursor = conn.cursor()
    
    query = """
    SELECT name, state, country, population, latitude, longitude, state_abbr, country_abbr, timezone_id
    FROM cities
    WHERE population BETWEEN ? AND ?
    ORDER BY timezone_id, population DESC
    """
    
    cursor.execute(query, (min_pop, max_pop))
    results = cursor.fetchall()
    conn.close()
    return results

def get_top_cities_per_tz_per_country(limit_per_group: int = 5) -> List[Tuple]:
    """
    Returns the top X cities for every country within each timezone.
    Groups by both Timezone AND Country.
    """
    conn = sqlite3.connect(CITIES_DB_PATH)
    cursor = conn.cursor()
    
    # Partitioning by two columns: timezone_id and country_abbr
    query = """
    WITH GroupedRanked AS (
        SELECT 
            name, state, country, population, latitude, longitude, 
            state_abbr, country_abbr, timezone_id,
            ROW_NUMBER() OVER (
                PARTITION BY timezone_id, country_abbr 
                ORDER BY population DESC
            ) as rank
        FROM cities
    )
    SELECT name, state, country, population, latitude, longitude, state_abbr, country_abbr, timezone_id
    FROM GroupedRanked
    WHERE rank <= ?
    ORDER BY timezone_id, country_abbr, population DESC
    """
    
    cursor.execute(query, (limit_per_group,))
    results = cursor.fetchall()
    conn.close()
    return results

def get_cities_range_per_tz_per_country(min_pop: int, max_pop: int) -> List[Tuple]:
    """
    Returns cities in a population range, sorted so they are 
    grouped by Timezone and then by Country.
    """
    conn = sqlite3.connect(CITIES_DB_PATH)
    cursor = conn.cursor()
    
    query = """
    SELECT name, state, country, population, latitude, longitude, state_abbr, country_abbr, timezone_id
    FROM cities
    WHERE population BETWEEN ? AND ?
    ORDER BY timezone_id, country_abbr, population DESC
    """
    
    cursor.execute(query, (min_pop, max_pop))
    results = cursor.fetchall()
    conn.close()
    return results

def get_cities_by_timezone(timezone_name: str) -> List[Tuple]:
    """
    Returns all cities belonging to a specific IANA timezone name.
    """
    conn = sqlite3.connect(CITIES_DB_PATH)
    cursor = conn.cursor()
    
    query = """
    SELECT 
        c.name, c.state, c.country, c.population, c.latitude, 
        c.longitude, c.state_abbr, c.country_abbr, c.timezone_id
    FROM cities c
    JOIN iana_timezones t ON c.timezone_id = t.id
    WHERE t.timezone_name = ?
    ORDER BY c.population DESC
    """
    
    cursor.execute(query, (timezone_name,))
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        print(f"No cities found for timezone: {timezone_name}")
        
    return results

def get_cities_by_timezone(timezone_name: str, limit: Optional[int] = None) -> List[Tuple]:
    """
    Returns cities belonging to a specific IANA timezone name.
    Optionally limited to the top X most populated cities.
    """
    conn = sqlite3.connect(CITIES_DB_PATH)
    cursor = conn.cursor()
    
    # If limit is None, we set it to -1 (SQLite returns all rows for -1)
    sql_limit = limit if limit is not None else -1
    
    query = """
    SELECT 
        c.name, c.state, c.country, c.population, c.latitude, 
        c.longitude, c.state_abbr, c.country_abbr, c.timezone_id
    FROM cities c
    JOIN iana_timezones t ON c.timezone_id = t.id
    WHERE t.timezone_name = ?
    ORDER BY c.population DESC
    LIMIT ?
    """
    
    cursor.execute(query, (timezone_name, sql_limit))
    results = cursor.fetchall()
    conn.close()
    
    return results

def get_cities_from_tz_table(timezone_name: str, limit: Optional[int] = None) -> List[Tuple]:
    """
    Retrieves cities directly from the specialized timezone table.
    This is faster than querying the master 'cities' table for large datasets.
    """
    # 1. Convert "Europe/London" to "tz_europe_london"
    table_name = sanitize_table_name(timezone_name)
    
    conn = sqlite3.connect(CITIES_DB_PATH)
    cursor = conn.cursor()
    
    # 2. Check if the table actually exists before querying
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if not cursor.fetchone():
        print(f"Table '{table_name}' does not exist. Run create_timezone_specific_tables() first.")
        conn.close()
        return []

    # 3. Build query with optional limit
    sql_limit = limit if limit is not None else -1
    
    # Note: Table names cannot be parameterized in SQL, so we use f-string 
    # but ONLY after sanitizing the input to prevent SQL injection.
    query = f"""
        SELECT name, state, country, population, latitude, longitude, state_abbr, country_abbr
        FROM {table_name}
        ORDER BY population DESC
        LIMIT ?
    """
    
    cursor.execute(query, (sql_limit,))
    results = cursor.fetchall()
    conn.close()
    
    return results

def get_cities_from_best_hour_match(target_hour: int, city_limit: Optional[int] = None) -> list:
    """
    Finds winning timezones and attaches local time, date, and abbr to city objects.
    """
    winning_meta = find_best_matching_timezones_with_meta(target_hour)
    
    all_cities = []
    if not winning_meta:
        return []

    for tz_name, meta in winning_meta.items():
        # Fetch raw city data from partitioned table
        raw_cities = get_cities_from_tz_table(tz_name, limit=city_limit)
        
        for city in raw_cities:
            # city is a tuple: (name, state, country, pop, lat, lon, s_abbr, c_abbr)
            # We convert to a dict to make the JSON output clear with the new fields
            city_dict = {
                "name": city[0],
                "state": city[1],
                "country": city[2],
                "population": city[3],
                "latitude": city[4],
                "longitude": city[5],
                "timezone": tz_name,
                "local_date": meta["date"],
                "local_time": meta["time"],
                "timezone_abbr": meta["abbr"]
            }
            all_cities.append(city_dict)

    return all_cities

def get_round_robin_cities(target_hour: int):
    """Retrieves cities for the target hour and organizes them by country."""
    from src.timezone_finder import find_best_matching_timezones_with_meta
    
    winning_meta = find_best_matching_timezones_with_meta(target_hour)
    if not winning_meta:
        return []

    # Group cities by country
    country_groups = {}
    
    for tz_name in winning_meta.keys():
        # Using your existing DB fetcher
        cities_in_tz = get_cities_from_tz_table(tz_name) 
        
        for city in cities_in_tz:
            # city tuple: (name, state, country, pop, lat, lon, ...)
            country = city[2]
            if country not in country_groups:
                country_groups[country] = []
            country_groups[country].append({
                "name": city[0],
                "country": city[2]
            })

    # Shuffle each group internally
    for country in country_groups:
        random.shuffle(country_groups[country])

    # Interleave (Round Robin)
    combined = []
    queues = [deque(cities) for cities in country_groups.values()]
    
    while queues:
        for q in list(queues):
            if q:
                combined.append(q.popleft())
            else:
                queues.remove(q)
                
    return combined