from datetime import datetime, timezone
import os
import sqlite3
from zoneinfo import ZoneInfo
import requests
import zipfile
import io
import json
import pycountry
import shutil
import random
from collections import defaultdict
from .constants import DATA_DIR, OUTPUT_DIR, CITIES_URL, ADMIN_URL, CITIES_FILE, ADMIN_FILE, DB_PATH

def download_geonames(force=False):
    """Downloads raw files. If force=True, replaces existing files."""
    if force and os.path.exists(DATA_DIR):
        print(f"🗑️ Force flag detected. Cleaning {DATA_DIR}...")
        shutil.rmtree(DATA_DIR)
        
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    for url, target in [(CITIES_URL, CITIES_FILE), (ADMIN_URL, ADMIN_FILE)]:
        if not os.path.exists(target) or force:
            print(f"📦 Downloading {url}...")
            r = requests.get(url)
            if "zip" in url:
                with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                    z.extractall(DATA_DIR)
            else:
                with open(target, "wb") as f:
                    f.write(r.content)

def aggregate_data(min_pop=500, force=False):
    """
    Builds the JSON database. 
    Only runs if JSON is missing or raw files are newer, unless force=True.
    """
    # Last-Modified Check
    if not force and os.path.exists(DB_PATH):
        db_time = os.path.getmtime(DB_PATH)
        raw_time = os.path.getmtime(CITIES_FILE)
        if db_time > raw_time:
            print("fast-forward: Database is already up to date.")
            return

    print(f"🏗️ Aggregating data (Force: {force})...")
    state_map = _load_admin_names()
    tz_to_location_data = defaultdict(list)

    with open(CITIES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            p = line.split("\t")
            pop = int(p[14])
            if pop < min_pop: continue
            
            city, country_code, admin1, tz = p[1], p[8], p[10], p[17].strip()
            state_name = state_map.get(f"{country_code}.{admin1}", admin1)
            
            try:
                country_name = pycountry.countries.get(alpha_2=country_code).name
            except:
                country_name = country_code

            tz_to_location_data[tz].append({
                "city": city,
                "state": state_name,
                "country": country_name,
                "population": pop
            })

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(tz_to_location_data, f, indent=4, ensure_ascii=False)
    print(f"✅ Grouped database built at {DB_PATH}")

def _load_admin_names():
    mapping = {}
    with open(ADMIN_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.split("\t")
            if len(parts) >= 2:
                mapping[parts[0]] = parts[1].strip()
    return mapping

def create_database_schema(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # IANA Table: Just the ID string
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS iana_timezones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timezone_id TEXT UNIQUE
        )
    """)

    # Locations Table: 1NF
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT,
            state TEXT,
            country TEXT,
            population INTEGER,
            iana_id INTEGER,
            FOREIGN KEY (iana_id) REFERENCES iana_timezones (id)
        )
    """)

    # Index for fast population filtering within a timezone
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_loc_iana_pop ON locations(iana_id, population DESC)")
    conn.commit()
    return conn

def populate_database(json_data, db_path):
    conn = create_database_schema(db_path)
    cursor = conn.cursor()
    
    # Assuming json_data is a flat list of city objects
    # We first extract unique timezones to populate the IANA table
    unique_tzs = {c['timezone_id'] for c in json_data}
    for tz in unique_tzs:
        cursor.execute("INSERT OR IGNORE INTO iana_timezones (timezone_id) VALUES (?)", (tz,))
    
    conn.commit()
    
    # Map TZ strings to IDs for the foreign key
    cursor.execute("SELECT id, timezone_id FROM iana_timezones")
    tz_lookup = {tz: i for i, tz in cursor.fetchall()}

    # Bulk insert locations
    city_data = [
        (c['city'], c.get('state', ''), c['country'], c['population'], tz_lookup[c['timezone_id']])
        for c in json_data
    ]
    cursor.executemany("""
        INSERT INTO locations (city, state, country, population, iana_id)
        VALUES (?, ?, ?, ?, ?)
    """, city_data)
    
    conn.commit()
    conn.close()
    
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