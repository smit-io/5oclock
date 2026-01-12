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
import sqlite3, json, os

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
    
def build_world_cities_db(json_path="world_cities.json", db_path="world_cities.db"):

    # Load JSON (accepts list or dict-of-lists keyed by timezone)
    with open(json_path, "r", encoding="utf-8") as f:
        src = json.load(f)

    cities = []
    if isinstance(src, dict):
        for tz, items in src.items():
            for it in items:
                if isinstance(it, dict):
                    if "iana_timezone" not in it or not it.get("iana_timezone"):
                        it["iana_timezone"] = tz
                    cities.append(it)
    elif isinstance(src, list):
        cities = src
    else:
        raise ValueError("Unsupported JSON structure for world_cities.json")

    # Create DB and schema
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS iana_timezones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timezone TEXT UNIQUE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT,
            state TEXT,
            state_abbrev TEXT,
            country TEXT,
            country_abbrev TEXT,
            population INTEGER,
            lat REAL,
            lng REAL,
            iana_timezone INTEGER,
            FOREIGN KEY (iana_timezone) REFERENCES iana_timezones(id)
        )
    """)
    conn.commit()

    # Insert unique timezones
    tzs = {c.get("iana_timezone") for c in cities if c.get("iana_timezone")}
    cur.executemany("INSERT OR IGNORE INTO iana_timezones (timezone) VALUES (?)", ((tz,) for tz in tzs))
    conn.commit()

    # Build timezone lookup
    cur.execute("SELECT id, timezone FROM iana_timezones")
    tz_lookup = {tz: id for id, tz in cur.fetchall()}

    # Normalize and insert city rows
    def safe_int(v):
        try: return int(v)
        except: return 0
    def safe_float(v):
        try: return float(v)
        except: return 0.0

    rows = []
    for c in cities:
        tz_id = tz_lookup.get(c.get("iana_timezone"))
        rows.append((
            c.get("city"),
            c.get("state") or c.get("province") or "",
            c.get("state_abbrev") or c.get("state_code") or "",
            c.get("country"),
            c.get("country_abbrev") or c.get("country_code") or "",
            safe_int(c.get("population") or c.get("pop")),
            safe_float(c.get("lat") or c.get("latitude")),
            safe_float(c.get("lng") or c.get("lon") or c.get("longitude")),
            tz_id
        ))

    cur.executemany("""
        INSERT INTO cities (city, state, state_abbrev, country, country_abbrev, population, lat, lng, iana_timezone)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()

    print(f"✅ Created {os.path.abspath(db_path)} ({len(rows)} cities, {len(tzs)} timezones)")