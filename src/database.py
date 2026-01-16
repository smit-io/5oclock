import sqlite3
import csv
from src.constants import GEONAMES_DB_PATH, INPUT_DIR, SCHEMAS, FILES_TO_DOWNLOAD, FORCE_UPDATE

def should_update_db() -> bool:
    """
    Checks if the database needs to be updated based on the force flag 
    or file timestamps.
    """
    if FORCE_UPDATE or not GEONAMES_DB_PATH.exists():
        return True

    db_mtime = GEONAMES_DB_PATH.stat().st_mtime
    
    # Check the 3 main source files
    source_files = ["cities500.txt", "admin1CodesASCII.txt", "countryInfo.txt"]
    for filename in source_files:
        file_path = INPUT_DIR / filename
        if file_path.exists():
            # If any source file is newer than the DB, we must update
            if file_path.stat().st_mtime > db_mtime:
                print(f"Source file {filename} is newer than database. Re-importing...")
                return True
                
    return False

def initialize_db():
    """Creates the database and tables if they don't exist."""
    GEONAMES_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(GEONAMES_DB_PATH)
    cursor = conn.cursor()
    
    for table_name, columns in SCHEMAS.items():
        cols_query = ", ".join([f"{c} TEXT" for c in columns])
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({cols_query})")
    
    conn.commit()
    return conn

def import_data():
    """Reads processed text files and loads them into SQLite only if necessary."""
    if not should_update_db():
        print("Database is already up to date with source files. Skipping import.")
        return

    conn = initialize_db()
    cursor = conn.cursor()

    targets = [
        ("cities500.txt", "cities", "cities"),
        ("admin1CodesASCII.txt", "admin_codes", "admin_codes"),
        ("countryInfo.txt", "country_info", "country_info")
    ]

    for filename, table_name, schema_key in targets:
        file_path = INPUT_DIR / filename
        if not file_path.exists():
            continue

        print(f"Updating table '{table_name}'...")
        cursor.execute(f"DELETE FROM {table_name}")

        with open(file_path, 'r', encoding='utf-8') as f:
            filtered_lines = (line for line in f if not line.startswith('#'))
            reader = csv.reader(filtered_lines, delimiter='\t', quoting=csv.QUOTE_NONE)
            placeholders = ', '.join(['?'] * len(SCHEMAS[schema_key]))
            cursor.executemany(f"INSERT INTO {table_name} VALUES ({placeholders})", reader)

    conn.commit()
    conn.close()
    print(f"Database successfully updated at: {GEONAMES_DB_PATH}")