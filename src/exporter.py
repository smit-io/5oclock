import json
import os
import sqlite3
from typing import List, Tuple, Optional

import pytz
from tqdm import tqdm
from src.constants import CITIES_DB_PATH, JSON_DIR, REFINED_SCHEMAS
from src.processor import get_cities_from_tz_table, sanitize_table_name

def _rows_to_dict_list(data: List[Tuple]) -> List[dict]:
    """Helper to convert list of tuples into a list of dictionaries using schema keys."""
    # REFINED_SCHEMAS["cities"] contains: ["name", "state", "country", "population", ...]
    keys = REFINED_SCHEMAS["cities"]
    return [dict(zip(keys, row)) for row in data]

def _handle_save(json_data: List[dict], filename: Optional[str], force: bool) -> str:
    """Helper to handle the file saving logic."""
    if not filename:
        return ""
    
    if not filename.endswith(".json"):
        filename += ".json"
        
    file_path = JSON_DIR / filename
    
    # --- ADD THIS LINE ---
    # This ensures /data/json/ exists before we try to write a file inside it.
    file_path.parent.mkdir(parents=True, exist_ok=True)
    # ---------------------
    
    if file_path.exists() and not force:
        print(f"File {filename} already exists. Skipping save (use force=True to overwrite).")
        return str(file_path)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=4, ensure_ascii=False)
    
    print(f"JSON saved to {file_path}")
    return str(file_path)

def export_table_to_json(table_name: str, filename: Optional[str] = None, force: bool = False) -> str:
    """Fetches data from a specific table in cities.db and converts to JSON."""
    conn = sqlite3.connect(CITIES_DB_PATH)
    cursor = conn.cursor()
    
    # Using the same column order as our internal refined schema
    cols = ", ".join(REFINED_SCHEMAS["cities"])
    cursor.execute(f"SELECT {cols} FROM {table_name}")
    rows = cursor.fetchall()
    conn.close()

    dict_data = _rows_to_dict_list(rows)
    _handle_save(dict_data, filename, force)
    return json.dumps(dict_data)

def export_list_to_json(data: List[Tuple], filename: Optional[str] = None, force: bool = False) -> str:
    """Converts a List[Tuple] (from get_ functions) into JSON."""
    if not data:
        print("No data provided to export.")
        return "[]"

    dict_data = _rows_to_dict_list(data)
    _handle_save(dict_data, filename, force)
    return json.dumps(dict_data)

# def export_all_timezones_to_json(limit_per_tz: Optional[int] = None, force: bool = False):
#     """
#     Iterates through all timezones in the database and exports 
#     each one as an individual JSON file.
#     """
#     conn = sqlite3.connect(CITIES_DB_PATH)
#     cursor = conn.cursor()

#     # Get all human-readable timezone names
#     cursor.execute("SELECT timezone_name FROM iana_timezones")
#     timezones = [row[0] for row in cursor.fetchall()]
#     conn.close()

#     print(f"Starting bulk JSON export for {len(timezones)} timezones...")

#     for tz_name in timezones:
#         # Get data using our partitioned table function for speed
#         cities_data = get_cities_from_tz_table(tz_name, limit=limit_per_tz)
        
#         if cities_data:
#             # Create a filename like "africa_cairo.json"
#             filename = sanitize_table_name(tz_name).replace("tz_", "")
#             export_list_to_json(cities_data, filename=filename, force=force)

#     print("Bulk export complete.")
    
def export_all_timezones_to_json(limit_per_tz: Optional[int] = None, force: bool = False):
    """
    Iterates through all timezones and exports data from the master 'cities' table.
    Uses the idx_cities_timezone index for high performance.
    """
    conn = sqlite3.connect(CITIES_DB_PATH)
    # Allows us to handle results as dictionaries
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Get the list of all valid timezones to process
    cursor.execute("SELECT timezone_name FROM iana_timezones")
    timezones = [row[0] for row in cursor.fetchall()]

    print(f"🚀 Starting bulk JSON export for {len(timezones)} timezones...")

    # 2. Iterate through each timezone and query the indexed master table
    for tz_name in tqdm(timezones, desc="Exporting JSONs", unit="tz"):
        
        # Define the output filename based on your previous logic
        # Result: "tz_america_new_york" -> "america_new_york"
        clean_filename = sanitize_table_name(tz_name).replace("tz_", "")
        file_path = os.path.join(JSON_DIR, f"{clean_filename}.json")

        # Skip if file exists and force is False
        if os.path.exists(file_path) and not force:
            continue

        # 3. Query the master 'cities' table directly
        query = """
            SELECT name, state, country, population, latitude, longitude, timezone_id 
            FROM cities 
            WHERE timezone_id = ?
            ORDER BY population DESC
        """
        
        if limit_per_tz:
            query += f" LIMIT {limit_per_tz}"

        cursor.execute(query, (tz_name,))
        
        # Convert sqlite3.Row objects to list of dicts for JSON
        cities_data = [dict(row) for row in cursor.fetchall()]
        
        if cities_data:
            # Reusing your existing helper to save the file
            export_list_to_json(cities_data, filename=clean_filename, force=force)

    conn.close()

# def export_all_timezones_to_json(limit_per_tz: int = None, force: bool = False):
#     """
#     Uses pytz to iterate through all valid IANA timezones and 
#     exports their corresponding database tables.
#     """
#     # Using pytz.common_timezones is often better for exports as it 
#     # excludes historical/redundant zones like 'Etc/GMT+1'
#     timezones = pytz.common_timezones 

#     print(f"Starting bulk JSON export for {len(timezones)} common timezones...")

#     for tz_name in timezones:
#         cities_data = get_cities_from_tz_table(tz_name, limit=limit_per_tz)
#         if cities_data:
#             filename = sanitize_table_name(tz_name).replace("tz_", "")
#             export_list_to_json(cities_data, filename=filename, force=force)
    
#     print("Bulk export complete.")