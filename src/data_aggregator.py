import os
import requests
import zipfile
import io
import json
import pycountry
import shutil
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